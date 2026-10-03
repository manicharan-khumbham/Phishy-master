#!/usr/bin/env python3
"""
Enhanced startup diagnostic script for the Phishing Platform
Run this before starting the main application to check all dependencies and services
"""

import sys
import os
import importlib
import subprocess
import json
import csv
from pathlib import Path
from datetime import datetime
import platform
import shutil

def print_header():
    """Print diagnostic header"""
    print("🚀 Phishy Platform - Startup Diagnostics")
    print("=" * 60)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

def check_python_version():
    """Check if Python version is compatible"""
    print("\n🐍 Checking Python Environment...")
    version = sys.version_info
    
    print(f"   Python Version: {version.major}.{version.minor}.{version.micro}")
    print(f"   Python Path: {sys.executable}")
    print(f"   Platform: {platform.python_implementation()}")
    
    if version.major == 3 and version.minor >= 8:
        print("   ✅ Python version is compatible")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.8+")
        return False

def check_package(package_name, import_name=None, version_attr=None):
    """Check if a package is installed and importable"""
    if import_name is None:
        import_name = package_name
    
    try:
        module = importlib.import_module(import_name)
        version = "unknown"
        
        # Try to get version information
        if version_attr and hasattr(module, version_attr):
            version = getattr(module, version_attr)
        elif hasattr(module, '__version__'):
            version = module.__version__
        elif hasattr(module, 'VERSION'):
            version = module.VERSION
        elif hasattr(module, 'version'):
            version = module.version
            
        print(f"   ✅ {package_name:<20} - {version}")
        return True, version
    except ImportError as e:
        print(f"   ❌ {package_name:<20} - MISSING ({str(e)[:50]})")
        return False, None
    except Exception as e:
        print(f"   ⚠️  {package_name:<20} - ERROR ({str(e)[:50]})")
        return False, None

def check_core_dependencies():
    """Check core FastAPI and web dependencies"""
    print("\n📦 Checking Core Dependencies...")
    
    core_packages = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pydantic", "pydantic"),
        ("httpx", "httpx"),
        ("python-multipart", "multipart"),
    ]
    
    all_good = True
    for package, import_name in core_packages:
        success, version = check_package(package, import_name)
        if not success:
            all_good = False
    
    return all_good

def check_data_dependencies():
    """Check data processing dependencies"""
    print("\n📊 Checking Data Processing Dependencies...")
    
    data_packages = [
        ("pandas", "pandas"),
        ("numpy", "numpy"), 
        ("polars", "polars")
    ]
    
    available = []
    for package, import_name in data_packages:
        success, version = check_package(package, import_name)
        if success:
            available.append(package)
    
    return available

def check_ai_dependencies():
    """Check AI and ML dependencies"""
    print("\n🧠 Checking AI/ML Dependencies...")
    
    ai_packages = [
        ("langchain", "langchain"),
        ("langchain-ollama", "langchain_ollama"),
        ("llama-index", "llama_index.core"),
        ("prophet", "prophet"),
        ("plotly", "plotly")
    ]
    
    available = []
    for package, import_name in ai_packages:
        success, version = check_package(package, import_name)
        if success:
            available.append(package)
    
    return available

def check_ollama_service():
    """Check if Ollama service is running and configured"""
    print("\n🤖 Checking Ollama Service...")
    
    # Check if ollama command exists
    ollama_path = shutil.which("ollama")
    if not ollama_path:
        print("   ❌ Ollama command not found in PATH")
        print("   💡 Install from: https://ollama.ai/download")
        return False
    
    print(f"   ✅ Ollama found at: {ollama_path}")
    
    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            # Check if service is running
            try:
                response = client.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    print("   ✅ Ollama service is running")
                    
                    # Check available models
                    models_data = response.json()
                    models = models_data.get("models", [])
                    
                    if models:
                        print(f"   📋 Available models: {len(models)}")
                        for model in models[:3]:  # Show first 3 models
                            name = model.get("name", "unknown")
                            size = model.get("size", 0)
                            size_gb = size / (1024**3) if size > 0 else 0
                            print(f"      - {name} ({size_gb:.1f}GB)")
                        
                        if len(models) > 3:
                            print(f"      ... and {len(models) - 3} more")
                    
                    # Check for Mistral specifically
                    mistral_found = any("mistral" in model.get("name", "") for model in models)
                    if mistral_found:
                        print("   ✅ Mistral model available")
                        return True
                    else:
                        print("   ⚠️  Mistral model not found")
                        print("   💡 Run: ollama pull mistral:7b")
                        return False
                else:
                    print(f"   ❌ Ollama service error: HTTP {response.status_code}")
                    return False
                    
            except httpx.ConnectError:
                print("   ❌ Cannot connect to Ollama service")
                print("   💡 Start with: ollama serve")
                return False
                
    except ImportError:
        print("   ❌ httpx not available - cannot test Ollama service")
        return False
    except Exception as e:
        print(f"   ❌ Error checking Ollama: {str(e)}")
        return False

def check_file_system():
    """Check file system setup and permissions"""
    print("\n📁 Checking File System Setup...")
    
    # Check required directories
    directories = ["data", "training", "logs", "routes"]
    for dir_name in directories:
        dir_path = Path(dir_name)
        
        if not dir_path.exists():
            try:
                dir_path.mkdir(exist_ok=True)
                print(f"   ✅ Created directory: {dir_name}")
            except Exception as e:
                print(f"   ❌ Failed to create {dir_name}: {e}")
                return False
        else:
            print(f"   ✅ Directory exists: {dir_name}")
        
        # Check write permissions
        if os.access(dir_path, os.W_OK):
            print(f"   ✅ Write access: {dir_name}")
        else:
            print(f"   ❌ No write access: {dir_name}")
            return False
    
    # Check/create essential files
    csv_file = Path("data/click_logs.csv")
    if not csv_file.exists():
        try:
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "user_email", "action_id", "ip_address", "user_agent", "referer"])
            print("   ✅ Created click_logs.csv with headers")
        except Exception as e:
            print(f"   ❌ Failed to create CSV file: {e}")
            return False
    else:
        print("   ✅ click_logs.csv exists")
    
    # Create routes __init__.py if needed
    routes_init = Path("routes/__init__.py")
    if not routes_init.exists():
        try:
            routes_init.parent.mkdir(exist_ok=True)
            routes_init.touch()
            print("   ✅ Created routes/__init__.py")
        except Exception as e:
            print(f"   ❌ Failed to create routes/__init__.py: {e}")
    
    return True

def check_application_files():
    """Check if main application files exist"""
    print("\n📄 Checking Application Files...")
    
    required_files = [
        ("app.py", "Main FastAPI application"),
        ("requirements.txt", "Python dependencies"),
    ]
    
    optional_files = [
        ("routes/click_tracker.py", "Click tracking module"),
        ("routes/llm_generator.py", "LLM email generation"),
        ("routes/analytics.py", "Analytics engine"),
        ("routes/phishing.py", "Basic phishing templates"),
    ]
    
    all_required = True
    
    # Check required files
    for file_path, description in required_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path:<25} - {description}")
        else:
            print(f"   ❌ {file_path:<25} - MISSING ({description})")
            all_required = False
    
    # Check optional files
    optional_count = 0
    for file_path, description in optional_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path:<25} - {description}")
            optional_count += 1
        else:
            print(f"   ⚠️  {file_path:<25} - Optional ({description})")
    
    print(f"   📊 Optional modules available: {optional_count}/{len(optional_files)}")
    
    return all_required

def test_imports():
    """Test importing key application modules"""
    print("\n🔍 Testing Module Imports...")
    
    # Test core app import
    try:
        sys.path.insert(0, os.getcwd())
        import app
        print("   ✅ app.py imports successfully")
        app_good = True
    except Exception as e:
        print(f"   ❌ app.py import failed: {e}")
        app_good = False
    
    # Test route modules
    route_modules = [
        "click_tracker",
        "llm_generator", 
        "analytics",
        "phishing",
        "admin_assistant",
        "historical_query",
        "forecast"
    ]
    
    working_routes = []
    for module_name in route_modules:
        try:
            module = importlib.import_module(f"routes.{module_name}")
            if hasattr(module, 'router'):
                print(f"   ✅ routes.{module_name} - router available")
                working_routes.append(module_name)
            else:
                print(f"   ⚠️  routes.{module_name} - no router attribute")
        except ImportError as e:
            print(f"   ❌ routes.{module_name} - import failed: {str(e)[:50]}")
        except Exception as e:
            print(f"   ⚠️  routes.{module_name} - error: {str(e)[:50]}")
    
    print(f"   📊 Working route modules: {len(working_routes)}/{len(route_modules)}")
    
    return app_good, working_routes

def generate_recommendations(results):
    """Generate recommendations based on diagnostic results"""
    print("\n💡 Recommendations:")
    print("-" * 40)
    
    if not results["python_ok"]:
        print("🔴 CRITICAL: Upgrade to Python 3.8 or higher")
    
    if not results["core_deps_ok"]:
        print("🔴 CRITICAL: Install core dependencies")
        print("   Run: pip install fastapi uvicorn pydantic httpx python-multipart")
    
    if not results["file_system_ok"]:
        print("🔴 CRITICAL: Fix file system permissions")
        print("   Check directory write permissions")
    
    if not results["app_imports_ok"]:
        print("🔴 CRITICAL: Fix application import errors")
        print("   Check app.py and route modules for syntax errors")
    
    if not results["ollama_ok"]:
        print("🟡 RECOMMENDED: Setup Ollama for AI features")
        print("   1. Install Ollama: https://ollama.ai/download")
        print("   2. Run: ollama serve")
        print("   3. Run: ollama pull mistral:7b")
        print("   Note: Platform will work in fallback mode without Ollama")
    
    if len(results["data_packages"]) < 2:
        print("🟡 RECOMMENDED: Install data processing packages")
        print("   Run: pip install pandas numpy polars")
    
    if len(results["ai_packages"]) < 3:
        print("🟡 OPTIONAL: Install AI packages for advanced features")
        print("   Run: pip install langchain llama-index prophet plotly")
    
    if len(results["working_routes"]) < 4:
        print("🟡 NOTICE: Some route modules are not working")
        print("   Check individual module import errors above")
    
    # Success scenarios
    if all([results["python_ok"], results["core_deps_ok"], results["file_system_ok"], results["app_imports_ok"]]):
        print("🟢 READY: Core platform is ready to start")
        
        if results["ollama_ok"]:
            print("🟢 ENHANCED: Full AI features available")
        else:
            print("🟡 BASIC: Running with basic features (AI in fallback mode)")

def print_startup_commands():
    """Print commands to start the platform"""
    print("\n🚀 Startup Commands:")
    print("-" * 40)
    print("Start the platform:")
    print("   uvicorn app:app --reload --host 0.0.0.0 --port 8000")
    print()
    print("Or use the run script:")
    print("   chmod +x run.sh")
    print("   ./run.sh")
    print()
    print("Or run directly:")
    print("   python app.py")
    print()
    print("Access points:")
    print("   🌐 Main API: http://localhost:8000")
    print("   📚 API Docs: http://localhost:8000/docs")
    print("   🎯 Training: http://localhost:8000/training/phishing-awareness.html")

def save_diagnostic_report(results):
    """Save diagnostic results to a file"""
    try:
        report_file = Path("logs/diagnostic_report.json")
        report_file.parent.mkdir(exist_ok=True)
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "platform": platform.system(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "diagnostic_results": results,
            "summary": {
                "core_ready": all([results["python_ok"], results["core_deps_ok"], results["file_system_ok"]]),
                "ai_ready": results["ollama_ok"],
                "total_routes": len(results["working_routes"]),
                "data_packages": len(results["data_packages"]),
                "ai_packages": len(results["ai_packages"])
            }
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📋 Diagnostic report saved: {report_file}")
        
    except Exception as e:
        print(f"\n⚠️ Could not save diagnostic report: {e}")

def main():
    """Run all diagnostic checks"""
    print_header()
    
    # Initialize results
    results = {
        "python_ok": False,
        "core_deps_ok": False,
        "data_packages": [],
        "ai_packages": [],
        "ollama_ok": False,
        "file_system_ok": False,
        "app_files_ok": False,
        "app_imports_ok": False,
        "working_routes": []
    }
    
    # Run all checks
    results["python_ok"] = check_python_version()
    results["core_deps_ok"] = check_core_dependencies()
    results["data_packages"] = check_data_dependencies()
    results["ai_packages"] = check_ai_dependencies()
    results["ollama_ok"] = check_ollama_service()
    results["file_system_ok"] = check_file_system()
    results["app_files_ok"] = check_application_files()
    
    # Test imports (only if basic requirements are met)
    if results["python_ok"] and results["core_deps_ok"] and results["file_system_ok"]:
        app_ok, working_routes = test_imports()
        results["app_imports_ok"] = app_ok
        results["working_routes"] = working_routes
    
    # Generate summary
    print("\n" + "=" * 60)
    print("📋 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    # Core readiness
    core_ready = all([results["python_ok"], results["core_deps_ok"], results["file_system_ok"]])
    
    if core_ready and results["app_imports_ok"]:
        print("🎉 PLATFORM STATUS: READY TO START")
        
        if results["ollama_ok"]:
            print("🚀 AI FEATURES: FULLY ENABLED")
        else:
            print("⚡ AI FEATURES: FALLBACK MODE (basic functionality)")
            
        print(f"📊 FEATURE SUMMARY:")
        print(f"   • Working route modules: {len(results['working_routes'])}")
        print(f"   • Data processing engines: {len(results['data_packages'])}")
        print(f"   • AI/ML packages: {len(results['ai_packages'])}")
        print(f"   • Ollama integration: {'✅' if results['ollama_ok'] else '❌'}")
        
    elif core_ready:
        print("⚠️  PLATFORM STATUS: NEEDS ATTENTION")
        print("   Core dependencies OK, but some modules have issues")
        
    else:
        print("❌ PLATFORM STATUS: NOT READY")
        print("   Critical dependencies missing")
    
    # Generate recommendations
    generate_recommendations(results)
    
    # Show startup commands if ready
    if core_ready:
        print_startup_commands()
    
    # Save report
    save_diagnostic_report(results)
    
    print("\n" + "=" * 60)
    print("Diagnostic complete! Check the recommendations above.")
    print("=" * 60)
    
    # Return appropriate exit code
    if core_ready and results["app_imports_ok"]:
        return 0  # Success
    elif core_ready:
        return 1  # Partial success
    else:
        return 2  # Critical issues

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)