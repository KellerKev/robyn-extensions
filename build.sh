#!/bin/bash
set -e

echo "🚀 Building Robyn Extensions..."

# Build Rust components
echo "📦 Building Rust workspace..."
cargo build --release --workspace

# Run Rust tests
echo "🧪 Running Rust tests..."
cargo test --workspace --release

# Build Python package
echo "🐍 Building Python package..."
cd robyn_python
pip install maturin
maturin develop --release
cd ..

# Run Python tests
echo "🧪 Running Python tests..."
pytest robyn_python/tests/ -v

echo "✅ Build complete!"
echo ""
echo "Try the examples:"
echo "  python examples/quickstart.py"
echo "  python examples/complete_example.py"
