#!/usr/bin/env python3
"""
Train all model variants (early and late prediction models)
"""

import subprocess
import sys
from pathlib import Path


def run_training(config_name: str, dry_run: bool = False, limit: int = None):
    """Run training for a specific config"""
    print(f"\n{'='*60}")
    print(f"🚀 Training {config_name} model...")
    print(f"{'='*60}")
    
    cmd = ["python", "ml_pipeline/main_train.py", config_name]
    
    if dry_run:
        cmd.append("--dry-run")
    
    if limit:
        cmd.extend(["--limit", str(limit)])
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Training completed successfully!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Training failed!")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Train all model variants')
    parser.add_argument('--dry-run', action='store_true', help='Run without saving models')
    parser.add_argument('--limit', type=int, help='Limit number of samples for testing')
    parser.add_argument('--early-only', action='store_true', help='Train only early model')
    parser.add_argument('--late-only', action='store_true', help='Train only late model')
    
    args = parser.parse_args()
    
    # Check if config files exist
    config_dir = Path("ml_pipeline/configs")
    early_config = config_dir / "result_model_early.yaml"
    late_config = config_dir / "result_model_late.yaml"
    
    if not early_config.exists():
        print(f"❌ Early config not found: {early_config}")
        sys.exit(1)
    
    if not late_config.exists():
        print(f"❌ Late config not found: {late_config}")
        sys.exit(1)
    
    print("🏗️  Training Football Prediction Model Variants")
    print(f"Dry run: {args.dry_run}")
    if args.limit:
        print(f"Sample limit: {args.limit}")
    
    success_count = 0
    total_count = 0
    
    # Train early model (no formations)
    if not args.late_only:
        total_count += 1
        if run_training("result_model_early", args.dry_run, args.limit):
            success_count += 1
    
    # Train late model (with formations)
    if not args.early_only:
        total_count += 1
        if run_training("result_model_late", args.dry_run, args.limit):
            success_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Training Summary")
    print(f"{'='*60}")
    print(f"✅ Successful: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 All models trained successfully!")
        
        if not args.dry_run:
            print("\n📁 Model files saved to: ml_pipeline/saved_models/")
            print("🔮 Ready for inference!")
            print("\nUsage examples:")
            print("  # Early prediction (no formations needed)")
            print("  python ml_pipeline/main_infer.py result_model_early")
            print("\n  # Late prediction (formations required)")  
            print("  python ml_pipeline/main_infer.py result_model_late")
        
        sys.exit(0)
    else:
        print(f"❌ {total_count - success_count} models failed to train")
        sys.exit(1)


if __name__ == "__main__":
    main() 