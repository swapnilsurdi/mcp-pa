#!/usr/bin/env python3
"""
Test Framework Validation Report
Validates all components of the comprehensive test suite
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

def validate_test_structure():
    """Validate test directory structure"""
    print("🏗️  Validating Test Structure...")
    
    required_dirs = [
        "tests/",
        "tests/unit/",
        "tests/integration/", 
        "tests/performance/"
    ]
    
    required_files = [
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/unit/test_models.py",
        "tests/unit/test_auth_service.py",
        "tests/unit/test_embedding_service.py",
        "tests/unit/test_intelligent_retrieval.py",
        "tests/integration/test_http_server.py",
        "tests/integration/test_database_integration.py",
        "tests/performance/test_performance.py",
        "pytest.ini",
        "scripts/run_tests.sh",
        "scripts/check_performance_regression.py"
    ]
    
    missing_dirs = []
    missing_files = []
    
    # Check directories
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_path)
    
    # Check files
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ Test structure validation passed")
    return True

def validate_test_content():
    """Validate test file content"""
    print("📝 Validating Test Content...")
    
    test_files = [
        "tests/unit/test_models.py",
        "tests/unit/test_auth_service.py", 
        "tests/integration/test_http_server.py",
        "tests/performance/test_performance.py"
    ]
    
    for test_file in test_files:
        try:
            with open(test_file, 'r') as f:
                content = f.read()
                
            # Basic validation - should contain test functions
            if "def test_" not in content:
                print(f"❌ {test_file} contains no test functions")
                return False
                
            # Should contain imports
            if "import" not in content:
                print(f"❌ {test_file} contains no imports")
                return False
                
            print(f"✅ {test_file} content validated")
            
        except Exception as e:
            print(f"❌ Error reading {test_file}: {e}")
            return False
    
    return True

def validate_configuration_files():
    """Validate configuration files"""
    print("⚙️  Validating Configuration Files...")
    
    # Check pytest.ini
    try:
        with open("pytest.ini", 'r') as f:
            pytest_content = f.read()
        
        required_config = [
            "testpaths", "markers", "addopts", "asyncio_mode"
        ]
        
        for config in required_config:
            if config not in pytest_content:
                print(f"❌ pytest.ini missing configuration: {config}")
                return False
        
        print("✅ pytest.ini validated")
        
    except Exception as e:
        print(f"❌ Error validating pytest.ini: {e}")
        return False
    
    # Check CI configuration
    if os.path.exists(".github/workflows/test.yml"):
        print("✅ GitHub Actions CI configuration found")
    else:
        print("⚠️  GitHub Actions CI configuration not found")
    
    return True

def validate_scripts():
    """Validate test execution scripts"""
    print("📜 Validating Test Scripts...")
    
    # Check run_tests.sh
    try:
        with open("scripts/run_tests.sh", 'r') as f:
            script_content = f.read()
        
        required_features = [
            "usage()", "build_pytest_cmd", "run_unit_tests", 
            "run_integration_tests", "run_performance_tests"
        ]
        
        for feature in required_features:
            if feature not in script_content:
                print(f"❌ run_tests.sh missing feature: {feature}")
                return False
        
        # Check if executable
        if not os.access("scripts/run_tests.sh", os.X_OK):
            print("❌ run_tests.sh is not executable")
            return False
            
        print("✅ run_tests.sh validated")
        
    except Exception as e:
        print(f"❌ Error validating run_tests.sh: {e}")
        return False
    
    # Check performance regression checker
    try:
        with open("scripts/check_performance_regression.py", 'r') as f:
            checker_content = f.read()
        
        if "PerformanceRegressionChecker" not in checker_content:
            print("❌ Performance regression checker missing main class")
            return False
            
        print("✅ Performance regression checker validated")
        
    except Exception as e:
        print(f"❌ Error validating performance checker: {e}")
        return False
    
    return True

def count_test_methods():
    """Count test methods in all test files"""
    print("🔢 Counting Test Methods...")
    
    test_counts = {}
    total_tests = 0
    
    test_dirs = ["tests/unit/", "tests/integration/", "tests/performance/"]
    
    for test_dir in test_dirs:
        if not os.path.exists(test_dir):
            continue
            
        dir_count = 0
        
        for file_path in Path(test_dir).glob("test_*.py"):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Count test functions
                file_tests = content.count("def test_")
                dir_count += file_tests
                
                print(f"  {file_path.name}: {file_tests} test methods")
                
            except Exception as e:
                print(f"❌ Error counting tests in {file_path}: {e}")
        
        test_counts[test_dir] = dir_count
        total_tests += dir_count
        print(f"  {test_dir} total: {dir_count} tests")
    
    print(f"\n📊 Total Test Methods: {total_tests}")
    return total_tests, test_counts

def generate_validation_summary():
    """Generate final validation summary"""
    print("\n" + "="*60)
    print("🎯 TEST FRAMEWORK VALIDATION SUMMARY")
    print("="*60)
    
    validation_results = {
        "timestamp": datetime.now().isoformat(),
        "validations_passed": [],
        "validations_failed": [],
        "test_counts": {},
        "overall_status": "UNKNOWN"
    }
    
    # Run all validations
    validations = [
        ("Test Structure", validate_test_structure),
        ("Test Content", validate_test_content),
        ("Configuration Files", validate_configuration_files),
        ("Test Scripts", validate_scripts)
    ]
    
    all_passed = True
    
    for name, validation_func in validations:
        try:
            result = validation_func()
            if result:
                validation_results["validations_passed"].append(name)
                print(f"✅ {name}: PASSED")
            else:
                validation_results["validations_failed"].append(name)
                print(f"❌ {name}: FAILED")
                all_passed = False
        except Exception as e:
            validation_results["validations_failed"].append(f"{name} (Exception)")
            print(f"❌ {name}: EXCEPTION - {e}")
            all_passed = False
    
    # Count tests
    total_tests, test_counts = count_test_methods()
    validation_results["test_counts"] = {
        "total": total_tests,
        "by_category": test_counts
    }
    
    # Overall status
    if all_passed and total_tests > 0:
        validation_results["overall_status"] = "SUCCESS"
        print(f"\n🎉 OVERALL STATUS: ✅ SUCCESS")
        print(f"✅ All validation checks passed")
        print(f"✅ {total_tests} test methods implemented")
        print(f"✅ Complete test infrastructure ready")
    else:
        validation_results["overall_status"] = "FAILED"
        print(f"\n🚨 OVERALL STATUS: ❌ FAILED")
        if validation_results["validations_failed"]:
            print(f"❌ Failed validations: {validation_results['validations_failed']}")
        if total_tests == 0:
            print(f"❌ No test methods found")
    
    # Save validation report
    try:
        with open("test_validation_results.json", 'w') as f:
            json.dump(validation_results, f, indent=2)
        print(f"\n📄 Validation results saved to: test_validation_results.json")
    except Exception as e:
        print(f"⚠️  Could not save validation results: {e}")
    
    return all_passed and total_tests > 0

if __name__ == "__main__":
    print("🧪 MCP Personal Assistant - Test Framework Validation")
    print("="*60)
    
    success = generate_validation_summary()
    
    if success:
        print(f"\n🚀 Test framework is ready for execution!")
        print(f"💡 Next steps:")
        print(f"   1. Install dependencies: pip install -r requirements-http.txt")
        print(f"   2. Run tests: ./scripts/run_tests.sh")
        print(f"   3. Run specific tests: ./scripts/run_tests.sh -t unit")
        print(f"   4. Run with benchmarks: ./scripts/run_tests.sh -b")
    
    sys.exit(0 if success else 1)