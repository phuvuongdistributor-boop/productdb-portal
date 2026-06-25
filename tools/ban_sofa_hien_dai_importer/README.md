# BÀN SOFA HIỆN ĐẠI Importer

Streamlit tool for importing the `BÀN SOFA HIỆN ĐẠI` image source into MASTER_PRODUCTDB V2.

## Run locally

```bash
cd tools/ban_sofa_hien_dai_importer
pip install -r requirements.txt
streamlit run app.py
```

## Current status

This is the first working skeleton. It already supports:

- Upload loose JPG/JPEG/PNG/WEBP images
- Upload ZIP archives
- Upload RAR archives gracefully
- Save files to `uploads/ban_sofa_hien_dai/`
- Build image manifest
- Classify images roughly into:
  - `single_product_image`
  - `composite_image`
  - `price_table_image`
  - `unknown`
- Export workbook `MASTER_IMPORT_BAN_SOFA_HIEN_DAI.xlsx`
- Export report `IMPORT_REPORT.txt`
- Workbook sheets:
  - `MAIN_IMPORT`
  - `UNMATCHED_SINGLE_PRODUCT`
  - `REVIEW_DUPLICATE`
  - `IMAGE_MANIFEST`
  - `TABLE_ROWS`

## Important business logic

Do **not** treat every image as one product.

Correct pipeline:

1. Extract archive/images.
2. Build image manifest.
3. Classify images.
4. OCR price table images first.
5. Extract table rows as primary source of ProductName, BasePrice, Size, Material, Description.
6. Match table rows to standalone product images.
7. Use composite images as reference/supporting evidence only.
8. Deduplicate visual repeats.
9. Export unique products to `MAIN_IMPORT`.
10. Put unmatched standalone images into `UNMATCHED_SINGLE_PRODUCT`.

## OCR provider

The app is prepared for an OCR provider wrapper.

Rules:

- Read credentials from runtime environment only.
- Do not commit secrets.
- If OCR is not configured, upload/storage/export should still work.

## RAR support

Python package `rarfile` also needs a system extractor such as `unrar`, `unar`, `bsdtar`, or `7z`.

If no extractor is available, the app shows a clear message and asks the user to upload ZIP or install an extractor.

## Next Codex tasks

1. Replace heuristic classifier with Vision-based classification.
2. Implement real OCR provider in `ocr_image()`.
3. Implement robust price table extraction.
4. Link table rows to standalone product images.
5. Add visual deduplication between standalone and composite images.
6. Add MASTER_PRODUCTDB duplicate checking.
7. Improve tests with the real `bàn sofa.rar` sample archive.
