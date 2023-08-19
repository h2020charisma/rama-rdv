import React, { useState } from 'react';

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
      // Handle excel upload logic here
      // ...
    }
  };

  return (
    <div>
      <h2>File Uploader</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label>
            <input
              type="radio"
              value="spectra"
              checked={uploadType === 'spectra'}
              onChange={handleUploadTypeChange}
            />
            Spectra Upload
          </label>
          <label>
            <input
              type="radio"
              value="excel"
              checked={uploadType === 'excel'}
              onChange={handleUploadTypeChange}
            />
            Excel Upload
          </label>
        </div>
        {uploadType === 'spectra' && (
          <div>
            {/* Add other input fields for spectra form */}
            <input
              type="file"
              accept=".txt, .csv"
              onChange={handleSpectraFileChange}
            />
            <input
              type="text"
              name="investigation"
              value={spectraFormData.investigation}
              onChange={(event) =>
                setSpectraFormData({ ...spectraFormData, investigation: event.target.value })
              }
              placeholder="Investigation"
            />
            <input
              type="text"
              name="provider"
              value={spectraFormData.provider}
              onChange={(event) =>
                setSpectraFormData({ ...spectraFormData, provider: event.target.value })
              }
              placeholder="Provider"
            />
            <input
              type="text"
              name="instrument"
              value={spectraFormData.instrument}
              onChange={(event) =>
                setSpectraFormData({ ...spectraFormData, instrument: event.target.value })
              }
              placeholder="Instrument"
            />  
            <input
              type="text"
              name="wavelength"
              value={spectraFormData.wavelength}
              onChange={(event) =>
                setSpectraFormData({ ...spectraFormData, wavelength: event.target.value })
              }
              placeholder="wavelength"
            />     
            <input
              type="text"
              name="sample"
              value={spectraFormData.sample}
              onChange={(event) =>
                setSpectraFormData({ ...spectraFormData, sample: event.target.value })
              }
              placeholder="sample"
            />                                    
            <input
              type="text"
              name="sample_provider"
              value={spectraFormData.sample_provider}
              onChange={(event) =>
                setSpectraFormData({ ...spectraFormData, sample_provider: event.target.value })
              }
              placeholder="sample_provider"
            /> 
            <button type="submit">Upload Spectra</button>
          </div>
        )}
        {uploadType === 'excel' && (
          <div>
            {/* Add input fields for excel form */}
            <input
              type="file"
              accept=".xlsx"
              onChange={handleExcelFileChange}
            />
            <input
              type="file"
              accept=".json"
              onChange={handleJsonFileChange}
            />
            <button type="submit">Upload Excel</button>
          </div>
        )}
      </form>
    </div>
  );
}

export default TWizardUploadApp;
