"""GxP AI Use-Case Assistant.

Import-order guard (Windows): onnxruntime (used by the local embedding model) fails with
"DLL load failed ... onnxruntime_pybind11_state" if PyMuPDF loads first, because the two
load conflicting versions of the Microsoft C++ runtime. Importing scikit-learn first loads a
compatible runtime. Every module under `app` imports this package first, so doing it here once
fixes the order everywhere. The clean fix is to install the latest Microsoft Visual C++
Redistributable; tests/test_retrieval_health.py fails loudly if dense retrieval is ever off.
"""
import sklearn  # noqa: F401  (must stay the first import, see above)
