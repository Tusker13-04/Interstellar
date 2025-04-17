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
    <div className="relative overflow-hidden z-10 bg-gray-800 p-8 rounded-lg shadow-md max-w-3xl mx-auto before:w-24 before:h-24 before:absolute before:bg-purple-600 before:rounded-full before:-z-10 before:blur-2xl after:w-32 after:h-32 after:absolute after:bg-sky-400 after:rounded-full after:-z-10 after:blur-xl after:top-24 after:-right-12">
  <h2 className="text-2xl font-bold text-white mb-6">Import / Export Data</h2>

  {error && (
    <div className="mb-4 p-4 bg-red-100 text-red-700 rounded">
      {error}
    </div>
  )}

  <div className="mb-6">
    <label className="block text-sm font-medium text-gray-300 mb-1">Import Items (CSV)</label>
    <input 
      type="file" 
      accept=".csv" 
      onChange={(e) => setItemsFile(e.target.files[0])} 
      className="w-full bg-gray-700 border border-gray-600 text-white p-2 rounded-md"
    />
    <button 
      onClick={() => handleFileUpload(itemsFile, importItems, 'Items')} 
      className="bg-gradient-to-r from-purple-600 via-purple-400 to-blue-500 text-white px-4 py-2 mt-3 font-bold rounded-md hover:opacity-80 w-full"
    >
      Upload Items
    </button>
  </div>

  <div className="mb-6">
    <label className="block text-sm font-medium text-gray-300 mb-1">Import Containers (CSV)</label>
    <input 
      type="file" 
      accept=".csv" 
      onChange={(e) => setContainersFile(e.target.files[0])} 
      className="w-full bg-gray-700 border border-gray-600 text-white p-2 rounded-md"
    />
    <button 
      onClick={() => handleFileUpload(containersFile, importContainers, 'Containers')} 
      className="bg-gradient-to-r from-purple-600 via-purple-400 to-blue-500 text-white px-4 py-2 mt-3 font-bold rounded-md hover:opacity-80 w-full"
    >
      Upload Containers
    </button>
  </div>

  <div className="mb-6">
    <button 
      onClick={handleExport} 
      className={`bg-gradient-to-r from-purple-600 via-purple-400 to-blue-500 text-white px-4 py-2 font-bold rounded-md w-full hover:opacity-80 ${exporting ? 'opacity-50 cursor-not-allowed' : ''}`} 
      disabled={exporting}
    >
      {exporting ? 'Exporting...' : 'Export Arrangement'}
    </button>
  </div>

  {importResult && (
    <div className={`mt-4 p-4 rounded-md ${importResult.success ? 'bg-green-100' : 'bg-yellow-100'}`}>
      <h3 className="text-lg font-semibold text-gray-800">{importResult.type} Results</h3>
      <p className="text-sm text-gray-700">{importResult.message}</p>
      {importResult.itemsImported !== undefined && (
        <p className="text-sm text-gray-700">
          {importResult.type === 'Items' ? 'Items' : 'Containers'} imported: {importResult.itemsImported}
        </p>
      )}
      {importResult.errors && importResult.errors.length > 0 && (
        <div className="mt-2">
          <h4 className="text-sm font-semibold text-red-700">Errors:</h4>
          <ul className="text-sm text-red-600 list-disc pl-5">
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
