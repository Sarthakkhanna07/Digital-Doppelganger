#!/usr/bin/env python3
"""
Time Capsule AI - Test Runner
Runs all tests and demos in the correct order
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*80}")
    print(f"🧪 {title}")
    print(f"{'='*80}")

def print_section(title: str):
    """Print a formatted section"""
    print(f"\n{'─'*60}")
    print(f"📋 {title}")
    print(f"{'─'*60}")

async def run_test_file(test_file: str, description: str):
    """Run a test file and return success status"""
    print_section(f"Running {description}")
    
    try:
        # Run the test file
        result = subprocess.run([
            sys.executable, test_file
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            if result.stdout:
                print("📄 Output:")
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stderr:
                print("🚨 Error:")
                print(result.stderr)
            if result.stdout:
                print("📄 Output:")
                print(result.stdout)
            return False
    
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

async def run_interactive_demo(demo_file: str, description: str):
    """Run an interactive demo"""
    print_section(f"Running {description}")
    print("💡 This is an interactive demo - follow the prompts")
    
    try:
        # Run the demo file interactively
        subprocess.run([sys.executable, demo_file], 
                      cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return True
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

async def main():
    """Run all tests and demos"""
    print_header("Time Capsule AI - Complete Test Suite")
    
    # Test results tracking
    test_results = []
    
    print("🚀 Starting comprehensive testing of Time Capsule AI...")
    print("📊 This will test all functionality including automatic delivery")
    
    # 1. Run comprehensive functionality tests
    success = await run_test_file(
        "tests/test_comprehensive.py",
        "Comprehensive Functionality Tests"
    )
    test_results.append(("Comprehensive Tests", success))
    
    # 2. Run automatic delivery tests (with immediate mode)
    print_section("Running Automatic Delivery Tests")
    print("🔧 Running automatic delivery test in immediate mode...")
    
    try:
        # Run with automatic input for immediate test
        result = subprocess.run([
            sys.executable, "tests/test_automatic_delivery.py"
        ], input="2\n", text=True, capture_output=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if "Manual trigger completed!" in result.stdout:
            print("✅ Automatic Delivery Tests - PASSED")
            print("📄 Key Output:")
            # Show just the delivery messages
            lines = result.stdout.split('\n')
            for i, line in enumerate(lines):
                if "AUTOMATIC DELIVERY" in line:
                    # Show the delivery block
                    for j in range(max(0, i-1), min(len(lines), i+10)):
                        print(lines[j])
                    break
            test_results.append(("Automatic Delivery", True))
        else:
            print("❌ Automatic Delivery Tests - FAILED")
            print(result.stdout)
            test_results.append(("Automatic Delivery", False))
    
    except Exception as e:
        print(f"❌ Automatic Delivery Tests - ERROR: {e}")
        test_results.append(("Automatic Delivery", False))
    
    # 3. Run user experience demo (with automatic input)
    print_section("Running User Experience Demo")
    print("🎭 Running user experience demo...")
    
    try:
        result = subprocess.run([
            sys.executable, "tests/demo_user_experience.py"
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if "Demo completed!" in result.stdout:
            print("✅ User Experience Demo - PASSED")
            print("📄 Key Output:")
            # Show user phone messages
            lines = result.stdout.split('\n')
            for i, line in enumerate(lines):
                if "USER'S PHONE" in line:
                    # Show the phone message block
                    for j in range(i, min(len(lines), i+8)):
                        if lines[j].strip():
                            print(lines[j])
                    break
            test_results.append(("User Experience Demo", True))
        else:
            print("❌ User Experience Demo - FAILED")
            print(result.stdout)
            test_results.append(("User Experience Demo", False))
    
    except Exception as e:
        print(f"❌ User Experience Demo - ERROR: {e}")
        test_results.append(("User Experience Demo", False))
    
    # Print final summary
    print_header("Test Results Summary")
    
    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)
    
    print(f"📊 Overall Results:")
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    print(f"📈 Success Rate: {(passed/total*100):.1f}%")
    
    print(f"\n📋 Detailed Results:")
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"🚀 Time Capsule AI is fully functional and ready for production!")
        print(f"✨ Features verified:")
        print(f"   • Emotional context capture")
        print(f"   • Natural language processing")
        print(f"   • Automatic reminder delivery")
        print(f"   • Timeline building and search")
        print(f"   • Tone personalization")
        print(f"   • Complete user experience flow")
    else:
        print(f"\n⚠️  Some tests failed. Please review the results above.")
    
    # Cleanup any test databases
    print(f"\n🧹 Cleaning up test files...")
    test_files = [
        "tests/test_time_capsule.db",
        "tests/test_delivery.db", 
        "tests/demo_user_experience.db"
    ]
    
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"   Removed {file}")
    
    print(f"✅ Cleanup completed!")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)