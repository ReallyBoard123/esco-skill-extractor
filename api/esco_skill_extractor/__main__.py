#!/usr/bin/env python3
"""ESCO Skill Extractor FastAPI Server

Main entry point for the ESCO Skill Extractor API server.
"""

import argparse
import uvicorn

from . import SkillExtractor
from .api import create_app


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="ESCO Skill Extractor: Extract ESCO skills and ISCO occupations from any text."
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="all-MiniLM-L6-v2",
        help="Model to use for skill extraction. Default is 'all-MiniLM-L6-v2'."
    )
    parser.add_argument(
        "--skill_threshold", "-s",
        type=float,
        default=0.6,
        help="Threshold for skill extraction. Default is 0.6"
    )
    parser.add_argument(
        "--occupation_threshold", "-o",
        type=float,
        default=0.55,
        help="Threshold for occupation extraction. Default is 0.55."
    )
    parser.add_argument(
        "--device", "-d",
        type=str,
        default=None,
        help="Device to use for computations. Default is cuda if available, else CPU."
    )
    parser.add_argument(
        "--host", "-c",
        type=str,
        default="localhost",
        help="Host to bind the server to. Default is localhost"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Port to bind the server to. Default is 8000"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    print(f"Initializing ESCO Skill Extractor (model: {args.model})...")
    
    # Initialize the skill extractor
    extractor = SkillExtractor(
        model=args.model,
        skills_threshold=args.skill_threshold,
        occupation_threshold=args.occupation_threshold,
        device=args.device,
    )
    
    print("Model loaded successfully!")
    
    # Create FastAPI app
    app = create_app(extractor, args.model)
    
    print(f"Starting ESCO Skill Extractor API at http://{args.host}:{args.port}")
    print(f"API documentation available at http://{args.host}:{args.port}/docs")
    print(f"Alternative docs at http://{args.host}:{args.port}/redoc")
    
    # Run the server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        reload=args.reload
    )


if __name__ == "__main__":
    main()