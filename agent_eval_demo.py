import json
from source_attribution import SourceAttribution

class MockAgentSystem:
    def __init__(self):
        self.attributor = SourceAttribution()

    def evaluate_and_cite(self, paper_id: str, generated_answer: str, is_hallucinated: bool):
        print(f"\n[AGENT] Câu trả lời sinh ra: '{generated_answer}'")
        print(f"[EVALUATOR] Đang kiểm tra tính chính xác...")
        
        if is_hallucinated:
            print("[EVALUATOR] [CẢNH BÁO] Phát hiện câu trả lời có dấu hiệu không chính xác hoặc thiếu căn cứ từ nguồn!")
            print("[SYSTEM] Đang truy xuất bằng chứng gốc từ tầng Clean...")
            
            # Lấy bằng chứng từ module SourceAttribution vừa tạo
            evidence = self.attributor.get_evidence(paper_id)
            
            print("\n--- BẰNG CHỨNG XUẤT TỪ NGUỒN (SOURCE ATTRIBUTION) ---")
            print(f"• Tên bài báo: {evidence.get('title')}")
            print(f"• Tác giả: {evidence.get('authors')}")
            print(f"• Link gốc: {evidence.get('abs_url')}")
            print(f"• Nội dung gốc đối chứng:\n  \"{evidence.get('source_text')[:300]}...\"")
            print("-----------------------------------------------------")
        else:
            print("[EVALUATOR] [OK] Câu trả lời khớp với nguồn dữ liệu.")

if __name__ == "__main__":
    system = MockAgentSystem()
    
    # Giả lập trường hợp Agent trả lời sai/bịa đặt dựa trên bài SafeRAG
    target_id = "10.2118/234689-pa"
    fake_answer = "SafeRAG sử dụng công nghệ lượng tử để dự đoán tai nạn mỏ dầu."
    
    system.evaluate_and_cite(paper_id=target_id, generated_answer=fake_answer, is_hallucinated=True)
