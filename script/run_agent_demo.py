from core import load_settings, write_json
from retrieval import LocalEmbeddingIndex, build_agent, run_agent_question

settings = load_settings()
index = LocalEmbeddingIndex.load(settings)
agent = build_agent(settings, index)

questions = [
    "Which papers discuss agentic retrieval augmented generation?",
    "Who authored the paper about roof design compliance?",
    "What is the newest paper in the corpus about?",
    "Do we have any paper about quantum cryptography?",   # phải trả lời "không có"
]
demo = [{"question": q, "answer": run_agent_question(agent, q)} for q in questions]
write_json(settings.paths.demo_answers, demo)