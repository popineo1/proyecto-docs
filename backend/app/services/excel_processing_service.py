import logging
import pandas as pd
import hashlib
import json
from pathlib import Path
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from dateutil import parser as date_parser
from sqlalchemy.orm import Session
from app.models.financial_movement import FinancialMovement

logger = logging.getLogger(__name__)

class ExcelProcessingService:
    # Semantic mapping for headers - APOCALYPSE EDITION
    HEADER_MAPPING = {
        "movement_date": ["Fecha", "F. emisión", "Fecha factura", "Date", "Fecha mov.", "Día", "Fec.", "Fecha contable", "Cuando pasó"],
        "third_party_name": ["Tercero", "Cliente", "Proveedor", "Empresa", "Nombre", "Acreedor", "Deudor", "Razón Social", "Client Name", "Supplier", "Vendor", "Pagador", "Beneficiario", "A quién le"],
        "concept": ["Concepto", "Descripción", "Detalle", "Observaciones", "Notes", "Description", "Memo", "Texto", "Operación", "Por qué le"],
        "net_amount": ["Base Imponible", "Base", "Neto", "Importe base", "Subtotal", "Net Amount", "Base sujeta"],
        "tax_amount": ["IVA", "Cuota IVA", "Impuesto", "VAT", "Tax", "Taxes", "Cuota"],
        "total_amount": ["Total", "Importe", "Total factura", "Importe final", "Total con IVA", "Salida", "Entrada", "Cargo", "Abono", "Debe", "Haber", "Total Amount", "Monto", "La Pasta Total"],
        "withholding_amount": ["IRPF General", "IRPF Alquiler", "Retención", "IRPF", "Ret."],
        "source_reference": ["Nº Factura", "Factura", "Referencia", "Ref.", "Doc."]
    }

    @staticmethod
    def _normalize_headers(row_list: list) -> dict:
        """Determines which column index corresponds to which model field."""
        mapping = {}
        for idx, cell in enumerate(row_list):
            if pd.isna(cell) or not isinstance(cell, str):
                continue
            
            clean_cell = cell.strip().lower()
            for field, aliases in ExcelProcessingService.HEADER_MAPPING.items():
                for alias in aliases:
                    if alias.lower() in clean_cell or clean_cell in alias.lower():
                        mapping[field] = idx
                        break
        return mapping

    @staticmethod
    def _find_table_start(df: pd.DataFrame) -> tuple[int, dict, bool]:
        """
        Finds the row index that contains the most recognized headers.
        Returns (best_row_idx, mapping, is_transactional).
        A sheet is 'transactional' if it has at least a Date and an Amount column.
        """
        best_row = 0
        best_mapping = {}
        max_matches = 0
        is_transactional = False

        # Scan up to the first 30 rows for a coherent transactional structure
        for i in range(min(30, len(df))):
            current_row = df.iloc[i].tolist()
            mapping = ExcelProcessingService._normalize_headers(current_row)
            
            # Density Check: Must have a Date and at least one Amount field
            has_date = "movement_date" in mapping
            has_amount = "total_amount" in mapping or "net_amount" in mapping
            
            if has_date and has_amount:
                # If we found the core, we prioritize the one with MOST matches overall
                if len(mapping) > max_matches:
                    max_matches = len(mapping)
                    best_row = i
                    best_mapping = mapping
                    is_transactional = True
        
        return best_row, best_mapping, is_transactional

    @staticmethod
    def _classify_sheet(sheet_name: str, mapping: dict, df: pd.DataFrame, header_row_idx: int) -> str:
        """Heuristic to decide if a sheet is 'income' or 'expense'."""
        s_name = sheet_name.lower()
        if any(w in s_name for w in ["venta", "ingreso", "facturación", "income", "sale", "emitida"]):
            return "income"
        if any(w in s_name for w in ["gasto", "compra", "inversión", "proveedor", "expense", "purchase", "vendor", "recibida"]):
            return "expense"
        
        # Check original column headers if mapped
        if "third_party_name" in mapping:
            headers = df.iloc[header_row_idx].tolist()
            tp_header = str(headers[mapping["third_party_name"]]).lower()
            if any(w in tp_header for w in ["cliente", "client", "customer", "deudor"]):
                return "income"
            if any(w in tp_header for w in ["proveedor", "supplier", "vendor", "acreedor"]):
                return "expense"
            
        return "expense" # Default

    @staticmethod
    def _generate_fingerprint(tenant_id: UUID, data: dict) -> str:
        hash_dict = {
            "tenant_id": str(tenant_id),
            "date": str(data.get("movement_date")),
            "third_party": str(data.get("third_party_name")).strip().lower(),
            "total": str(data.get("total_amount")),
            "reference": str(data.get("source_reference")).strip().lower() if data.get("source_reference") else "",
            "kind": data.get("kind"),
            "concept": str(data.get("concept")).strip().lower() if data.get("concept") else ""
        }
        encoded = json.dumps(hash_dict, sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _get_movement_category(tp_name: str, concept: str) -> str:
        """Bi-dimensional classification based on Brand/Vendor and Concept."""
        tp = str(tp_name or "").lower()
        cp = str(concept or "").lower()
        
        # 1. Personal / Seguros Sociales
        if any(w in cp for w in ["nómina", "nomina", "salario", "sueldo", "tc1", "tc2", "mutua", "irpf trabajadores", "autónomo", "autonomo", "ss"]) or \
           any(w in tp for w in ["seguridad social", "mutua"]):
            return "Personal / Seguros Sociales"
            
        # 2. Impuestos
        if any(w in tp for w in ["hacienda", "aeat", "agencia tributaria", "ayuntamiento"]) or \
           any(w in cp for w in ["iva", "modelo 303", "modelo 130", "modelo 111", "modelo 115", "impuesto", "ibi", "tasa"]):
            return "Impuestos"
            
        # 3. Suscripciones / Software
        if any(w in cp for w in ["software", "licencia", "hosting", "servidor", "suscripcion", "suscripción"]) or \
           any(w in tp for w in ["aws", "amazon web", "google", "microsoft", "apple", "mailchimp", "openai", "hostinger"]):
            return "Suscripciones / Software"
            
        # 4. Suministros
        if any(w in cp for w in ["luz", "agua", "gas", "internet", "teléfono", "telefono"]) or \
           any(w in tp for w in ["iberdrola", "endesa", "naturgy", "vodafone", "movistar", "orange"]):
            return "Suministros"
            
        # 5. Alquileres
        if any(w in cp for w in ["alquiler", "arrendamiento", "coworking", "oficina", "local"]) or \
           any(w in tp for w in ["wework"]):
            return "Alquileres"
            
        # 6. Financiero
        if any(w in cp for w in ["comisión", "comision", "intereses", "mantenimiento", "transferencia"]) or \
           any(w in tp for w in ["banco", "bbva", "santander", "caixa"]):
            return "Financiero"
            
        # 7. Viajes / Dietas
        if any(w in cp for w in ["hotel", "vuelo", "tren", "restaurante", "comida", "dieta", "uber", "cabify", "taxi", "ave"]) or \
           any(w in tp for w in ["renfe", "uber", "cabify"]):
            return "Viajes / Dietas"
            
        # 8. Servicios Profesionales
        if any(w in cp for w in ["asesoría", "asesoria", "abogado", "consultoría", "gestoría", "notario", "notaría"]):
            return "Servicios Profesionales"
            
        return "General"

    @staticmethod
    def _check_exists(db: Session, fingerprint: str) -> bool:
        return db.query(FinancialMovement).filter(FinancialMovement.fingerprint == fingerprint).first() is not None

    @staticmethod
    def preview_document(file_path: str) -> dict:
        """
        Analyzes an Excel file and returns a structural preview.
        """
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}

        try:
            with pd.ExcelFile(path) as xls:
                preview = {"sheets": []}

                for sheet_name in xls.sheet_names:
                    # Use header=None to ensure _find_table_start sees the actual header row
                    df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                    if df.empty:
                        continue

                    header_row, mapping, is_transactional = ExcelProcessingService._find_table_start(df)
                    if not is_transactional:
                        logger.info(f"[Preview] Skipping sheet '{sheet_name}': Insufficient transactional structure detected (Date + Amount required).")
                        continue

                    # Sample some data for classification
                    kind = ExcelProcessingService._classify_sheet(sheet_name, mapping, df, header_row)
                    
                    # Sample some rows
                    sample_rows = []
                    for i in range(header_row + 1, min(header_row + 6, len(df))):
                        sample_rows.append(df.iloc[i].fillna("").to_dict())

                    preview["sheets"].append({
                        "name": sheet_name,
                        "kind": kind,
                        "header_row": int(header_row),
                        "columns_detected": list(mapping.keys()),
                        "total_rows_detected": int(len(df) - header_row - 1),
                        "sample": sample_rows
                    })

                return preview
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    @staticmethod
    def process_document(db: Session, tenant_id: UUID, document_id: UUID, file_path: str) -> int:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return 0

        try:
            with pd.ExcelFile(path) as xls:
                total_metrics = {"imported": 0, "duplicates": 0, "skipped": 0, "errors": 0}
                logger.info(f"--- Starting processing for document {document_id} ---")

                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                    metrics = ExcelProcessingService._process_generic_sheet(db, tenant_id, document_id, sheet_name, df)
                    
                    total_metrics["imported"] += metrics["imported"]
                    total_metrics["duplicates"] += metrics["duplicates"]
                    total_metrics["skipped"] += metrics["skipped"]
                    total_metrics["errors"] += metrics["errors"]
                    
                    logger.info(f"Sheet '{sheet_name}': {metrics['imported']} records created.")

                logger.info(f"--- Finished processing document {document_id}: {total_metrics} ---")
                return total_metrics
        except Exception as e:
            logger.error(f"Error processing Excel {file_path}: {str(e)}")
            raise e

    @staticmethod
    def _process_generic_sheet(db: Session, tenant_id: UUID, document_id: UUID, sheet_name: str, df: pd.DataFrame) -> dict:
        if df.empty:
            return {"imported": 0, "duplicates": 0, "skipped": 0, "errors": 0}
            
        header_row, mapping, is_transactional = ExcelProcessingService._find_table_start(df)
        if not is_transactional:
            logger.info(f"Sheet '{sheet_name}' skipped: Insufficient transactional structure detected.")
            return {"imported": 0, "duplicates": 0, "skipped": 1, "errors": 0}

        logger.info(f"Sheet '{sheet_name}': Transactional table found at row {header_row}. Mapping: {list(mapping.keys())}")

        kind = ExcelProcessingService._classify_sheet(sheet_name, mapping, df, header_row)
        
        # Deduce 'kind' from Total column header if specialized names exist
        headers = df.iloc[header_row].tolist()
        total_header = str(headers[mapping["total_amount"]]).lower() if "total_amount" in mapping else ""
        if any(w in total_header for w in ["entrada", "abono", "haber"]):
            kind = "income"
        elif any(w in total_header for w in ["salida", "cargo", "debe"]):
            kind = "expense"

        imported = 0
        skipped_duplicate = 0
        skipped_empty = 0
        skipped_error = 0
        
        # Process from header_row + 1 onwards
        for i in range(header_row + 1, len(df)):
            row = df.iloc[i]
            
            try:
                # Extract values using mapping
                m_date_val = row.iloc[mapping["movement_date"]] if "movement_date" in mapping else None
                total_val = row.iloc[mapping["total_amount"]] if "total_amount" in mapping else None

                # Relaxed check: Only skip if date is missing. 
                # Total can be zero if we have net/tax for healing.
                if pd.isna(m_date_val):
                    skipped_empty += 1
                    continue
                
                m_date = ExcelProcessingService._to_date(m_date_val)
                total = ExcelProcessingService._to_decimal(total_val)
                
                # Garbage Drop: Silent skip if data is logically empty or broken (missing both date and meaningful amount)
                if (m_date is None or pd.isna(m_date)) and total == 0:
                    continue
                
                # Bi-dimensional Garbage Drop: If date exists but we have no amount info at all (garbage row like "Error")
                # we only skip if total, base AND iva are effectively zero/none
                raw_base = row.iloc[mapping["net_amount"]] if "net_amount" in mapping else None
                if total == 0 and (pd.isna(raw_base) or raw_base == "Error"):
                    # This row is likely a comment or a junk row like Row 6 in 'Gastos Operativos'
                    continue
                
                # Local row kind deduction
                kind_to_save = kind
                if total < 0:
                    # Business Requirement #3: Maintain negative for 'Notes de Abono'
                    kind_to_save = "expense"
                elif total > 0 and sheet_name.lower() == "movimientos sin factura":
                    kind_to_save = "income"

                tp_name = str(row.iloc[mapping["third_party_name"]]) if "third_party_name" in mapping and not pd.isna(row.iloc[mapping["third_party_name"]]) else "Desconocido"
                ref = str(row.iloc[mapping["source_reference"]]) if "source_reference" in mapping and not pd.isna(row.iloc[mapping["source_reference"]]) else None
                concept = str(row.iloc[mapping["concept"]]) if "concept" in mapping and not pd.isna(row.iloc[mapping["concept"]]) else f"Importado de {sheet_name}"
                
                base = ExcelProcessingService._to_decimal(row.iloc[mapping["net_amount"]]) if "net_amount" in mapping else Decimal("0.00")
                iva = ExcelProcessingService._to_decimal(row.iloc[mapping["tax_amount"]]) if "tax_amount" in mapping else Decimal("0.00")
                withholding = ExcelProcessingService._to_decimal(row.iloc[mapping["withholding_amount"]]) if "withholding_amount" in mapping else Decimal("0.00")

                # --- MATH HEALING LAYER (SaaS-Ready) ---
                # 1. Missing Total
                if total == 0 and base != 0:
                    total = base + iva - withholding
                
                # 2. Missing Base (Net)
                if base == 0 and total != 0:
                    if "nómina" in concept.lower() or "nomina" in concept.lower():
                        base = total
                        iva = Decimal("0.00")
                    else:
                        base = total - iva + withholding # Simplistic healing

                fingerprint = ExcelProcessingService._generate_fingerprint(tenant_id, {
                    "movement_date": m_date,
                    "third_party_name": tp_name,
                    "total_amount": total,
                    "source_reference": ref,
                    "kind": kind_to_save,
                    "concept": concept
                })

                if ExcelProcessingService._check_exists(db, fingerprint):
                    skipped_duplicate += 1
                    continue

                # Smart Categorization Logic
                category = ExcelProcessingService._get_movement_category(tp_name, concept)
                
                # Fallback for specific sheets
                if category == "General":
                    if sheet_name == "Ventas": category = "Ventas"
                    elif "alquiler" in sheet_name.lower() or withholding > 0: category = "Alquileres"

                # Detect if this is a 'Proposed' or 'Manual' movement
                is_manual_sheet = sheet_name.lower() in ["movimientos sin factura", "movimientos", "banco", "extracto"]
                m_status = "proposed" if is_manual_sheet else "confirmed"
                m_source = "bank_import" if is_manual_sheet else "excel_import"

                movement = FinancialMovement(
                    tenant_id=tenant_id,
                    source_document_id=document_id,
                    source_type=m_source,
                    kind=kind_to_save,
                    movement_date=m_date,
                    source_reference=ref,
                    net_amount=base,
                    tax_amount=iva,
                    withholding_amount=withholding,
                    total_amount=total,
                    third_party_name=tp_name,
                    concept=concept,
                    category=category,
                    status=m_status,
                    needs_review=is_manual_sheet,
                    fingerprint=fingerprint,
                    source_data=json.dumps(row.to_dict(), default=str)
                )
                db.add(movement)
                imported += 1
            except Exception as e:
                skipped_error += 1
                logger.error(f"Fallo crítico en fila {i} de '{sheet_name}': {str(e)}")

        logger.info(f"Sheet summary: {imported} imported, {skipped_duplicate} duplicates, {skipped_empty} empty/invalid, {skipped_error} errors.")
        db.commit()
        return {
            "imported": imported,
            "duplicates": skipped_duplicate,
            "skipped": skipped_empty,
            "errors": skipped_error
        }

    @staticmethod
    def _to_decimal(value) -> Decimal:
        if pd.isna(value) or value == "":
            return Decimal("0.00")
        if isinstance(value, (int, float, Decimal)):
            return Decimal(str(value)).quantize(Decimal("0.01"))
        
        if isinstance(value, str):
            clean_val = value.replace("€", "").replace("$", "").strip()
            # Handle European format (1.234,56) vs US (1,234.56)
            if "," in clean_val and "." in clean_val:
                if clean_val.find(",") > clean_val.find("."): # 1.234,56
                    clean_val = clean_val.replace(".", "").replace(",", ".")
                else: # 1,234.56
                    clean_val = clean_val.replace(",", "")
            elif "," in clean_val:
                parts = clean_val.split(",")
                if len(parts[-1]) <= 2: clean_val = clean_val.replace(",", ".")
                else: clean_val = clean_val.replace(",", "")
            
            try:
                return Decimal(clean_val).quantize(Decimal("0.01"))
            except:
                return Decimal("0.00")
        return Decimal("0.00")

    @staticmethod
    def _to_date(value) -> datetime:
        if isinstance(value, datetime):
            return value
        if pd.isna(value) or value == "":
            return None
            
        if isinstance(value, str):
            try:
                # dateutil handles multiple formats and dayfirst=True is more standard for EU
                return date_parser.parse(value, dayfirst=True)
            except:
                return None
        return None
