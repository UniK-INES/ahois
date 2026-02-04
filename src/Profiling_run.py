import cProfile
import pstats
import sys

# --- Configuration ---
target_script = "Run.py"
output_file = "output.prof"

print(f"--- Starting Profiling of {target_script} ---")

with cProfile.Profile() as pr:
    try:
        with open(target_script, "rb") as f:
            code = compile(f.read(), target_script, 'exec')
        exec(code, {"__name__": "__main__", "__file__": target_script})
    except SystemExit:
        pass
    except Exception as e:
        print(f"Script crashed: {e}")
        raise e

# Save file
stats = pstats.Stats(pr)
stats.dump_stats(output_file)
print(f"\n--- Data saved to {output_file} ---")

# --- 🐍 SIMPLER LAUNCHER ---
try:
    # Import SnakeViz directly to avoid path issues
    from snakeviz.cli import main as snakeviz_main
    
    print("Launching SnakeViz in browser...")
    # Trick SnakeViz into thinking it was run from command line
    sys.argv = ["snakeviz", output_file]
    snakeviz_main()
    
except ImportError:
    print("\n SnakeViz is still not installed!")
    print("Run this command in your terminal to fix it:")
    print(f'"{sys.executable}" -m pip install snakeviz')