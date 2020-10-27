# ribs
Rust Service to be called from inside python

This is some rust code that is meant to be installed as a python wheel on the repository and used

It uses [pyo3](https://pyo3.rs) as the binding and [maturin](https://github.com/PyO3/maturin) as the tool that turns the rust code into python

We hope it provides a new level of speed to the CPU-bound parts of the code 
