from src.phase1.phase1_pipeline import Phase1Pipeline

pipeline = Phase1Pipeline(
    master_list_path="data/master_list.txt",
    bond_pdf_path="data/bond_memorandum.pdf"
)

master_key, cleaned_pages, full_text = pipeline.run()