import os
import argparse
import uvicorn
from dotenv import load_dotenv

def main():
    parser = argparse.ArgumentParser(description="AI Support & TAM Tooling")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Command: serve
    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to listen on")

    # Command: index
    index_parser = subparsers.add_parser("index", help="Build the RAG knowledge base index")
    index_parser.add_argument("--force", action="store_true", help="Force rebuild existing index")

    # Command: eval
    eval_parser = subparsers.add_parser("eval", help="Run the evaluation harness")

    # Command: ui
    ui_parser = subparsers.add_parser("ui", help="Start the Streamlit UI")

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    if not args.command:
        parser.print_help()
        return

    if args.command == "serve":
        # Ensure index exists before starting
        from src.rag.indexer import build_index
        build_index(force_rebuild=False)
        print(f"Starting FastAPI server on {args.host}:{args.port}")
        uvicorn.run("src.api:app", host=args.host, port=args.port, reload=True)

    elif args.command == "index":
        from src.rag.indexer import build_index
        count = build_index(force_rebuild=args.force)
        print(f"Successfully indexed {count} knowledge base chunks.")

    elif args.command == "eval":
        if not os.getenv("GROQ_API_KEY"):
            print("ERROR: GROQ_API_KEY environment variable is required to run evaluations.")
            return
        from src.rag.indexer import build_index
        build_index(force_rebuild=False)
        
        from src.eval.harness import run_evals
        run_evals()

    elif args.command == "ui":
        import subprocess
        print("Starting Streamlit UI...")
        subprocess.run(["streamlit", "run", "src/ui/app.py"])

if __name__ == "__main__":
    main()
