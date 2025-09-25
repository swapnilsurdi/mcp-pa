#!/usr/bin/env python3
"""
Performance Regression Checker

Analyzes benchmark results and checks for performance regressions
against established baselines.
"""

import json
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# Performance baselines (in milliseconds for mean response time)
PERFORMANCE_BASELINES = {
    "test_dashboard_benchmark": {
        "max_mean_time": 100.0,  # 100ms max mean time
        "max_stddev": 50.0,      # 50ms max standard deviation
        "description": "Dashboard response time"
    },
    "test_project_creation_benchmark": {
        "max_mean_time": 150.0,  # 150ms max mean time
        "max_stddev": 75.0,      # 75ms max standard deviation
        "description": "Project creation time"
    },
    "test_search_benchmark": {
        "max_mean_time": 80.0,   # 80ms max mean time
        "max_stddev": 40.0,      # 40ms max standard deviation
        "description": "Search response time"
    }
}

class PerformanceRegressionChecker:
    """Check for performance regressions in benchmark results"""
    
    def __init__(self, benchmark_file: str):
        self.benchmark_file = benchmark_file
        self.results = None
        self.regressions = []
        self.warnings = []
        
    def load_results(self) -> bool:
        """Load benchmark results from file"""
        try:
            with open(self.benchmark_file, 'r') as f:
                self.results = json.load(f)
            return True
        except FileNotFoundError:
            print(f"❌ Benchmark file not found: {self.benchmark_file}")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in benchmark file: {e}")
            return False
        except Exception as e:
            print(f"❌ Error loading benchmark file: {e}")
            return False
    
    def analyze_benchmarks(self) -> None:
        """Analyze benchmark results for regressions"""
        if not self.results or 'benchmarks' not in self.results:
            print("❌ No benchmark data found in results")
            return
        
        print(f"📊 Analyzing {len(self.results['benchmarks'])} benchmarks...")
        print()
        
        for benchmark in self.results['benchmarks']:
            self._check_benchmark_performance(benchmark)
    
    def _check_benchmark_performance(self, benchmark: Dict[str, Any]) -> None:
        """Check individual benchmark performance"""
        name = benchmark.get('name', 'unknown')
        fullname = benchmark.get('fullname', name)
        
        # Extract test method name for baseline lookup
        test_method = name.split('.')[-1] if '.' in name else name
        
        if test_method not in PERFORMANCE_BASELINES:
            print(f"⚠️  No baseline defined for {test_method}")
            return
        
        baseline = PERFORMANCE_BASELINES[test_method]
        stats = benchmark.get('stats', {})
        
        # Get timing statistics (in seconds, convert to milliseconds)
        mean_time_ms = stats.get('mean', 0) * 1000
        stddev_ms = stats.get('stddev', 0) * 1000
        min_time_ms = stats.get('min', 0) * 1000
        max_time_ms = stats.get('max', 0) * 1000
        
        print(f"📈 {baseline['description']}:")
        print(f"   Mean: {mean_time_ms:.2f}ms (baseline: {baseline['max_mean_time']:.2f}ms)")
        print(f"   StdDev: {stddev_ms:.2f}ms (baseline: {baseline['max_stddev']:.2f}ms)")
        print(f"   Range: {min_time_ms:.2f}ms - {max_time_ms:.2f}ms")
        
        # Check for regressions
        regression_found = False
        
        if mean_time_ms > baseline['max_mean_time']:
            self.regressions.append({
                'test': test_method,
                'metric': 'mean_time',
                'actual': mean_time_ms,
                'baseline': baseline['max_mean_time'],
                'description': baseline['description']
            })
            print(f"   ❌ REGRESSION: Mean time {mean_time_ms:.2f}ms exceeds baseline {baseline['max_mean_time']:.2f}ms")
            regression_found = True
        
        if stddev_ms > baseline['max_stddev']:
            self.regressions.append({
                'test': test_method,
                'metric': 'stddev',
                'actual': stddev_ms,
                'baseline': baseline['max_stddev'],
                'description': baseline['description']
            })
            print(f"   ❌ REGRESSION: StdDev {stddev_ms:.2f}ms exceeds baseline {baseline['max_stddev']:.2f}ms")
            regression_found = True
        
        # Check for warnings (approaching limits)
        warning_threshold = 0.8  # 80% of baseline
        
        if not regression_found:
            if mean_time_ms > baseline['max_mean_time'] * warning_threshold:
                self.warnings.append({
                    'test': test_method,
                    'metric': 'mean_time',
                    'actual': mean_time_ms,
                    'baseline': baseline['max_mean_time'],
                    'percentage': (mean_time_ms / baseline['max_mean_time']) * 100
                })
                print(f"   ⚠️  WARNING: Mean time approaching baseline ({mean_time_ms/baseline['max_mean_time']*100:.1f}%)")
            else:
                print(f"   ✅ Performance within acceptable range")
        
        print()
    
    def generate_report(self) -> None:
        """Generate final performance report"""
        print("=" * 60)
        print("📋 PERFORMANCE REGRESSION REPORT")
        print("=" * 60)
        
        if not self.results:
            print("❌ No benchmark results to analyze")
            return
        
        # Summary statistics
        machine_info = self.results.get('machine_info', {})
        commit_info = self.results.get('commit_info', {})
        datetime_str = self.results.get('datetime', 'unknown')
        
        print(f"📅 Test Date: {datetime_str}")
        print(f"💻 Machine: {machine_info.get('machine', 'unknown')} ({machine_info.get('processor', 'unknown')})")
        print(f"🐍 Python: {machine_info.get('python_version', 'unknown')}")
        
        if commit_info:
            print(f"🔧 Commit: {commit_info.get('id', 'unknown')[:8]}")
            print(f"🌿 Branch: {commit_info.get('branch', 'unknown')}")
        
        print()
        
        # Regression summary
        if self.regressions:
            print(f"❌ REGRESSIONS FOUND: {len(self.regressions)}")
            print()
            
            for regression in self.regressions:
                print(f"   • {regression['description']} ({regression['metric']})")
                print(f"     Actual: {regression['actual']:.2f}ms")
                print(f"     Baseline: {regression['baseline']:.2f}ms")
                print(f"     Regression: {((regression['actual'] / regression['baseline'] - 1) * 100):+.1f}%")
                print()
        else:
            print("✅ NO REGRESSIONS FOUND")
        
        # Warning summary
        if self.warnings:
            print(f"⚠️  PERFORMANCE WARNINGS: {len(self.warnings)}")
            print()
            
            for warning in self.warnings:
                print(f"   • {warning['test']} ({warning['metric']}): {warning['percentage']:.1f}% of baseline")
        else:
            print("✅ NO PERFORMANCE WARNINGS")
        
        print()
        
        # Overall status
        if self.regressions:
            print("🚨 OVERALL STATUS: PERFORMANCE REGRESSION DETECTED")
            return False
        elif self.warnings:
            print("⚠️  OVERALL STATUS: PERFORMANCE WARNINGS (acceptable)")
            return True
        else:
            print("✅ OVERALL STATUS: ALL PERFORMANCE TARGETS MET")
            return True
    
    def save_historical_data(self) -> None:
        """Save benchmark results to historical data file"""
        if not self.results:
            return
        
        history_file = "performance_history.json"
        history = []
        
        # Load existing history
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
            except Exception as e:
                print(f"⚠️  Could not load performance history: {e}")
        
        # Add current results
        current_entry = {
            'timestamp': datetime.now().isoformat(),
            'datetime': self.results.get('datetime'),
            'commit': self.results.get('commit_info', {}),
            'machine': self.results.get('machine_info', {}),
            'benchmarks': {}
        }
        
        for benchmark in self.results.get('benchmarks', []):
            name = benchmark.get('name', '').split('.')[-1]
            stats = benchmark.get('stats', {})
            
            current_entry['benchmarks'][name] = {
                'mean_ms': stats.get('mean', 0) * 1000,
                'stddev_ms': stats.get('stddev', 0) * 1000,
                'min_ms': stats.get('min', 0) * 1000,
                'max_ms': stats.get('max', 0) * 1000,
                'rounds': stats.get('rounds', 0)
            }
        
        history.append(current_entry)
        
        # Keep only last 50 entries
        if len(history) > 50:
            history = history[-50:]
        
        # Save updated history
        try:
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
            print(f"📊 Performance data saved to {history_file}")
        except Exception as e:
            print(f"⚠️  Could not save performance history: {e}")
    
    def run(self) -> bool:
        """Run complete performance regression check"""
        print("🔍 PERFORMANCE REGRESSION CHECKER")
        print("=" * 60)
        print()
        
        if not self.load_results():
            return False
        
        self.analyze_benchmarks()
        success = self.generate_report()
        
        # Save historical data for trend analysis
        self.save_historical_data()
        
        return success


def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python check_performance_regression.py <benchmark_results.json>")
        sys.exit(1)
    
    benchmark_file = sys.argv[1]
    
    checker = PerformanceRegressionChecker(benchmark_file)
    success = checker.run()
    
    # Exit with error code if regressions found
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()