# Workflow to cpnvert Raman spectra to NeXuS format using pyambit

This is ploomber workflow with starting point pipeline.yaml .
- copy env_example.yaml to env.yaml and edit if necessary

```
ploomber build -e pipeline.yaml 
```

The NeXus files will be in output_folder . 
The generated notebook in products/convert2nexus.ipynb