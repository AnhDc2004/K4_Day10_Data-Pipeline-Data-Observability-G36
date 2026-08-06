import json
from pathlib import Path

class SourceAttribution:
    def __init__(self, clean_data_dir: str = "data/clean"):
        self.clean_data_dir = Path(clean_data_dir)
        self.papers_cache = self._load_all_papers()

    def _load_all_papers(self) -> dict:
        """Đọc toàn bộ dữ liệu clean để tra cứu nhanh theo paper_id"""
        papers_dict = {}
        if self.clean_data_dir.exists():
            for file_path in self.clean_data_dir.glob("*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and "paper_id" in item:
                                    papers_dict[item["paper_id"]] = item
                    except Exception:
                        pass
        return papers_dict

    def get_evidence(self, paper_id: str) -> dict:
        """
        Trích xuất bằng chứng chi tiết từ nguồn sạch khi cần đối chiếu
        """
        paper = self.papers_cache.get(paper_id)
        if not paper:
            return {"error": f"Không tìm thấy paper_id: {paper_id} trong nguồn dữ liệu sạch."}
        
        # Trả về các trường bằng chứng quan trọng
        return {
            "paper_id": paper.get("paper_id"),
            "title": paper.get("title"),
            "authors": paper.get("authors_joined"),
            "source_text": paper.get("summary"), # Hoặc text_for_embedding
            "abs_url": paper.get("abs_url"),
            "pdf_url": paper.get("pdf_url"),
            "comment": paper.get("comment")
        }

# --- Kiểm tra thử module ---
if __name__ == "__main__":
    attributor = SourceAttribution()
    
    # Thử kiểm tra bằng chứng cho bài SafeRAG mà chúng ta đã test
    test_id = "10.2118/234689-pa"
    evidence = attributor.get_evidence(test_id)
    
    print("=== BẰNG CHỨNG XUẤT TỪ NGUỒN ===")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
