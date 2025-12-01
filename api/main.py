#!/usr/bin/env python3
"""Clean main entry point for ESCO API"""

import argparse
import uvicorn

from app import create_app


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="ESCO Skill Extractor API")
    parser.add_argument("--model", type=str, default="BAAI/bge-m3", help="Model name")
    parser.add_argument("--skills-threshold", type=float, default=0.6, help="Skills threshold")
    parser.add_argument("--occupations-threshold", type=float, default=0.55, help="Occupations threshold")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host")
    parser.add_argument("--port", type=int, default=8000, help="Port")
    parser.add_argument("--device", type=str, default=None, help="Device (cuda/cpu)")
    parser.add_argument("--reload", action="store_true", help="Enable reload")
    
    args = parser.parse_args()
    
    try:
        # Create app
        app = create_app(
            model=args.model,
            skills_threshold=args.skills_threshold,
            occupation_threshold=args.occupations_threshold,
            device=args.device
        )
        
        # Start server
        print(f"✅ Starting server at http://{args.host}:{args.port}")
        print(f"📖 Docs: http://{args.host}:{args.port}/docs")
        
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())