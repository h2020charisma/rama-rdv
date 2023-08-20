import React, { useState } from 'react';
import './TWizardUploadApp.css';
interface SpectraFormData {
  provider: string;
  instrument: string;
  wavelength: string;
  investigation: string;
  sample: string;
  sample_provider: string;
  project: string;
  spectraFile: File | null;
}

interface ExcelFormData {
  excelFile: File | null;
  jsonFile: File | null;
}

function TWizardUploadApp() {
  const [uploadType, setUploadType] = useState<'spectra' | 'excel'>('spectra');
  const [spectraFormData, setSpectraFormData] = useState<SpectraFormData>({
    provider: '',
    instrument: '',
    wavelength: '',
    investigation: '',
    sample: '',
    sample_provider: '',
    project: '',
    spectraFile: null
  });
  const [excelFormData, setExcelFormData] = useState<ExcelFormData>({
    excelFile: null,
    jsonFile: null
  });

  const handleUploadTypeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setUploadType(event.target.value as 'spectra' | 'excel');
  };

  const handleSpectraFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0] || null;
    setSpectraFormData((prevData) => ({ ...prevData, spectraFile: selectedFile }));
  };

  const handleExcelFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0] || null;

    setExcelFormData((prevData) => ({ ...prevData, excelFile: selectedFile }));
  };

  const handleJsonFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0] || null;
    setExcelFormData((prevData) => ({ ...prevData, jsonFile: selectedFile }));
  };
  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (uploadType === 'spectra') {
      // Handle spectra upload logic here
      // ...
    } else if (uploadType === 'excel') {
      // Access excelFormData
      const { excelFile, jsonFile } = excelFormData;
    
      // Check if both excelFile and jsonFile are not null
      if (excelFile && jsonFile) {
        // You can use excelFile and jsonFile here for further processing
        console.log('Excel File:', excelFile);
        console.log('JSON File:', jsonFile);

        // Perform your upload or processing logic here
      } else {
        // Handle error case where files are not selected
        console.log('Please select both Excel and JSON files.');
      }
    }
  };

  return (
    <div className="container mt-5">
      <h2 className="mb-4">File Uploader</h2>
      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label className="me-3">
            <input
              type="radio"
              value="spectra"
              checked={uploadType === 'spectra'}
              onChange={handleUploadTypeChange}
              className="me-1"
            />
            Spectra Upload
          </label>
          <label>
            <input
              type="radio"
              value="excel"
              checked={uploadType === 'excel'}
              onChange={handleUploadTypeChange}
              className="me-1"
            />
            Excel Upload
          </label>
        </div>
        {uploadType === 'spectra' && (
          <div>
            {/* Add other input fields for spectra form */}
            <div className="row mb-3">
                <input
                  type="file"
                  accept=".txt, .csv"
                  onChange={handleSpectraFileChange}
                />
            </div>
            <div className="row mb-3">
              <div className="col-md-6">
                <input
                  type="text"
                  className="form-control"
                  name="investigation"
                  value={spectraFormData.investigation}
                  onChange={(event) =>
                    setSpectraFormData({ ...spectraFormData, investigation: event.target.value })
                  }
                  placeholder="Investigation"
                />
              </div>
              <div className="col-md-6">
                <input
                  type="text"
                  className="form-control"
                  name="provider"
                  value={spectraFormData.provider}
                  onChange={(event) =>
                    setSpectraFormData({ ...spectraFormData, provider: event.target.value })
                  }
                  placeholder="Provider"
                />
              </div>              
            </div>
            <div className="row mb-3">
              <div className="col-md-6">
                <input
                  type="text"
                  className="form-control"
                  name="instrument"
                  value={spectraFormData.instrument}
                  onChange={(event) =>
                    setSpectraFormData({ ...spectraFormData, instrument: event.target.value })
                  }
                  placeholder="instrument"
                />
              </div>
              <div className="col-md-6">
                <input
                  type="text"
                  className="form-control"
                  name="wavelength"
                  value={spectraFormData.wavelength}
                  onChange={(event) =>
                    setSpectraFormData({ ...spectraFormData, wavelength: event.target.value })
                  }
                  placeholder="wavelength"
                />
              </div>              
            </div>
            <div className="row">
            <div className="col-md-6">
                <input
                  type="text"
                  className="form-control"
                  name="wavelength"
                  value={spectraFormData.sample}
                  onChange={(event) =>
                    setSpectraFormData({ ...spectraFormData, sample: event.target.value })
                  }
                  placeholder="sample"
                />
              </div>  
              <div className="col-md-6">
                <input
                  type="text"
                  className="form-control"
                  name="sample_provider"
                  value={spectraFormData.sample_provider}
                  onChange={(event) =>
                    setSpectraFormData({ ...spectraFormData, sample_provider: event.target.value })
                  }
                  placeholder="sample_provider"
                />
              </div>                
            </div>
            <button type="submit" className="btn btn-primary">Upload Spectra</button>
          </div>
        )}
        {uploadType === 'excel' && (
          <div>
            <div className="row mb-3">
              {/* Add input fields for excel form */}
              <div className="col-md-6">
                <input
                  type="file"
                  accept=".xlsx"
                  onChange={handleExcelFileChange}
                />
              </div>
            </div>
            <div className="row mb-3">
              <div className="col-md-6">
                <input
                  type="file"
                  accept=".json"
                  onChange={handleJsonFileChange}
                />
              </div>
            </div>
            <button type="submit" className="btn btn-primary">Upload Excel</button>
          </div>
        )}
      </form>
    </div>
  );
  
}

export default TWizardUploadApp;
