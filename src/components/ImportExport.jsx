import { useState } from 'react';
import { importItems, importContainers, exportArrangement } from '../services/apiService';

const ImportExport = () => {
  const [itemsFile, setItemsFile] = useState(null);
  const [containersFile, setContainersFile] = useState(null);
  const [importResult, setImportResult] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);

  const handleFileUpload = async (file, importFunction, type) => {
    if (!file) {
      setError(`Please select a ${type} file!`);
      return;
    }

    if (!file.name.endsWith('.csv')) {
      setError('Please select a CSV file!');
      return;
    }

    try {
      setError(null);
      const response = await importFunction(file);
      setImportResult({ 
        type, 
        success: response.success,
        message: response.message,
        itemsImported: response.items_imported || response.containers_imported,
        errors: response.errors || []
      });
    } catch (error) {
      console.error(`Import ${type} Error:`, error);
      setError(`Failed to import ${type}: ${error.message}`);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    setError(null);
    try {
      await exportArrangement();
      setImportResult({
        type: 'Export',
        success: true,
        message: 'Arrangement exported successfully'
      });
    } catch (error) {
      console.error('Export Error:', error);
      setError(`Failed to export arrangement: ${error.message}`);
    }
    setExporting(false);
  };

  return (
    <div className="bg-white shadow-lg rounded-lg p-6 w-full max-w-3xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">Import / Export Data</h2>

      {error && (
        <div className="mb-4 p-4 bg-red-100 text-red-700 rounded">
          {error}
        </div>
      )}

      <div className="mb-4">
        <label className="block text-gray-600 font-semibold">Import Items (CSV)</label>
        <input 
          type="file" 
          accept=".csv" 
          onChange={(e) => setItemsFile(e.target.files[0])} 
          className="w-full border p-2 rounded" 
        />
        <button 
          onClick={() => handleFileUpload(itemsFile, importItems, 'Items')} 
          className="bg-blue-500 text-white px-4 py-2 mt-2 rounded w-full hover:bg-blue-600"
        >
          Upload Items
        </button>
      </div>

      <div className="mb-4">
        <label className="block text-gray-600 font-semibold">Import Containers (CSV)</label>
        <input 
          type="file" 
          accept=".csv" 
          onChange={(e) => setContainersFile(e.target.files[0])} 
          className="w-full border p-2 rounded" 
        />
        <button 
          onClick={() => handleFileUpload(containersFile, importContainers, 'Containers')} 
          className="bg-green-500 text-white px-4 py-2 mt-2 rounded w-full hover:bg-green-600"
        >
          Upload Containers
        </button>
      </div>

      <div className="mb-4">
        <button 
          onClick={handleExport} 
          className="bg-purple-500 text-white px-4 py-2 rounded w-full hover:bg-purple-600" 
          disabled={exporting}
        >
          {exporting ? 'Exporting...' : 'Export Arrangement'}
        </button>
      </div>

      {importResult && (
        <div className={`mt-4 p-4 rounded ${importResult.success ? 'bg-green-100' : 'bg-yellow-100'}`}>
          <h3 className="text-lg font-semibold">{importResult.type} Results</h3>
          <p className="text-sm text-gray-700">{importResult.message}</p>
          {importResult.itemsImported !== undefined && (
            <p className="text-sm text-gray-700">
              {importResult.type === 'Items' ? 'Items' : 'Containers'} imported: {importResult.itemsImported}
            </p>
          )}
          {importResult.errors && importResult.errors.length > 0 && (
            <div className="mt-2">
              <h4 className="text-sm font-semibold">Errors:</h4>
              <ul className="text-sm text-red-600">
                {importResult.errors.map((error, index) => (
                  <li key={index}>Row {error.row}: {error.message}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ImportExport;
