import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, FileText, Plus, Edit, Trash2, Save, X, ArrowLeft, Loader2, AlertCircle } from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Admin() {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newFileName, setNewFileName] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    try {
      const response = await axios.get(`${API}/admin/knowledge-files`);
      setFiles(response.data.files || []);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch knowledge files:", err);
      setError("Failed to load knowledge files");
      setLoading(false);
    }
  };

  const handleFileSelect = async (filename) => {
    try {
      setError("");
      const response = await axios.get(`${API}/admin/knowledge-files/${filename}`);
      setFileContent(response.data.content);
      setOriginalContent(response.data.content);
      setSelectedFile(filename);
      setEditing(false);
      setCreating(false);
    } catch (err) {
      console.error("Failed to fetch file content:", err);
      setError("Failed to load file content");
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      await axios.put(`${API}/admin/knowledge-files/${selectedFile}`, {
        content: fileContent
      });
      setSuccess("File saved successfully!");
      setOriginalContent(fileContent);
      setEditing(false);
      fetchFiles();
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save file");
    }
    setSaving(false);
  };

  const handleCreate = async () => {
    if (!newFileName.trim()) {
      setError("Please enter a filename");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const response = await axios.post(`${API}/admin/knowledge-files`, {
        filename: newFileName,
        content: fileContent
      });
      setSuccess("File created successfully!");
      setCreating(false);
      setNewFileName("");
      fetchFiles();
      handleFileSelect(response.data.filename);
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create file");
    }
    setSaving(false);
  };

  const handleDelete = async (filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    try {
      await axios.delete(`${API}/admin/knowledge-files/${filename}`);
      setSuccess("File deleted successfully!");
      if (selectedFile === filename) {
        setSelectedFile(null);
        setFileContent("");
      }
      fetchFiles();
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to delete file");
    }
  };

  const handleCancel = () => {
    if (editing) {
      setFileContent(originalContent);
      setEditing(false);
    }
    if (creating) {
      setCreating(false);
      setNewFileName("");
      setFileContent("");
    }
  };

  const startNewFile = () => {
    setCreating(true);
    setEditing(true);
    setSelectedFile(null);
    setNewFileName("");
    setFileContent(`# SECTOR: NEW_SECTOR
# Applies to: Description of companies this applies to

## SECTOR CLASSIFICATION SIGNALS
A company should be routed to this template if:
- Signal 1
- Signal 2

## KEY METRICS TO TRACK
- Metric 1
- Metric 2

## FINANCIAL MODEL STRUCTURE
Describe the P&L and Balance Sheet structure

## VALUATION METHODOLOGY
Describe how to value companies in this sector
`);
  };

  const hasChanges = fileContent !== originalContent;

  return (
    <div className="min-h-screen bg-slate-950 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 text-slate-400 hover:text-white mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </button>
          <div className="flex items-center gap-3 mb-2">
            <ShieldCheck className="w-8 h-8 text-indigo-400" />
            <h1 className="text-3xl md:text-4xl font-bold text-white">Admin Panel</h1>
          </div>
          <p className="text-slate-400">Manage sector knowledge files for financial modeling</p>
        </div>

        {/* Alerts */}
        {error && (
          <div className="mb-4 p-4 bg-red-900/30 border border-red-700 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-400">{error}</span>
            <button onClick={() => setError("")} className="ml-auto text-red-400 hover:text-red-300">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
        {success && (
          <div className="mb-4 p-4 bg-green-900/30 border border-green-700 rounded-lg text-green-400">
            {success}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* File List */}
          <div className="glass-card p-6 rounded-lg">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white">Knowledge Files</h2>
              <button 
                onClick={startNewFile}
                className="text-indigo-400 hover:text-indigo-300 p-2 rounded-lg hover:bg-slate-800 transition-colors"
                title="Create new file"
                data-testid="create-file-button"
              >
                <Plus className="w-5 h-5" />
              </button>
            </div>
            
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
              </div>
            ) : (
              <div className="space-y-2">
                {files.map((file) => (
                  <div
                    key={file.filename}
                    className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                      selectedFile === file.filename
                        ? 'bg-indigo-600/20 border border-indigo-600'
                        : 'hover:bg-slate-800 border border-transparent'
                    }`}
                  >
                    <button
                      onClick={() => handleFileSelect(file.filename)}
                      className="flex-1 flex items-center gap-3 text-left"
                      data-testid={`file-${file.filename}`}
                    >
                      <FileText className="w-5 h-5 text-indigo-400 flex-shrink-0" />
                      <div className="min-w-0">
                        <div className="text-white font-medium truncate">{file.filename}</div>
                        <div className="text-xs text-slate-500 truncate">{file.sector}</div>
                      </div>
                    </button>
                    {!['banks.md', 'generic.md'].includes(file.filename) && (
                      <button
                        onClick={() => handleDelete(file.filename)}
                        className="p-1 text-slate-500 hover:text-red-400 transition-colors"
                        title="Delete file"
                        data-testid={`delete-${file.filename}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
                {files.length === 0 && (
                  <p className="text-slate-500 text-center py-4">No knowledge files found</p>
                )}
              </div>
            )}
          </div>

          {/* Editor */}
          <div className="lg:col-span-2 glass-card p-6 rounded-lg">
            {selectedFile || creating ? (
              <>
                <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                  {creating ? (
                    <div className="flex items-center gap-2 flex-1">
                      <input
                        type="text"
                        value={newFileName}
                        onChange={(e) => setNewFileName(e.target.value)}
                        placeholder="filename (e.g., nbfc)"
                        className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500 w-48"
                        data-testid="new-filename-input"
                      />
                      <span className="text-slate-400">.md</span>
                    </div>
                  ) : (
                    <h2 className="text-xl font-semibold text-white">{selectedFile}</h2>
                  )}
                  
                  <div className="flex gap-2">
                    {editing ? (
                      <>
                        <button
                          onClick={creating ? handleCreate : handleSave}
                          disabled={saving || (!creating && !hasChanges)}
                          className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
                          data-testid="save-button"
                        >
                          {saving ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Save className="w-4 h-4" />
                          )}
                          {creating ? 'Create' : 'Save'}
                        </button>
                        <button
                          onClick={handleCancel}
                          className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
                          data-testid="cancel-button"
                        >
                          <X className="w-4 h-4" />
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => setEditing(true)}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
                        data-testid="edit-button"
                      >
                        <Edit className="w-4 h-4" />
                        Edit
                      </button>
                    )}
                  </div>
                </div>

                {hasChanges && !creating && (
                  <div className="mb-4 text-sm text-yellow-400">
                    * You have unsaved changes
                  </div>
                )}

                <textarea
                  value={fileContent}
                  onChange={(e) => setFileContent(e.target.value)}
                  disabled={!editing}
                  className="w-full h-[500px] md:h-[600px] bg-slate-900 border border-slate-700 rounded-lg p-4 text-slate-300 font-mono text-sm focus:outline-none focus:border-indigo-500 disabled:opacity-60 resize-none"
                  placeholder="Enter knowledge file content..."
                  data-testid="file-editor"
                />
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-[600px] text-center">
                <FileText className="w-16 h-16 text-slate-700 mb-4" />
                <p className="text-slate-500 mb-4">Select a file to view or edit</p>
                <button
                  onClick={startNewFile}
                  className="text-indigo-400 hover:text-indigo-300 flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Create new knowledge file
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Info */}
        <div className="mt-8 glass-card p-6 rounded-lg">
          <h3 className="text-lg font-semibold text-white mb-3">About Knowledge Files</h3>
          <div className="text-slate-400 text-sm leading-relaxed space-y-2">
            <p>
              Knowledge files define how Mosaic models companies in each sector. Each <code className="bg-slate-800 px-1 rounded">.md</code> file contains:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Sector classification rules (how to identify companies)</li>
              <li>Key metrics to track (NIM, CASA ratio for banks, etc.)</li>
              <li>Financial model structure (P&L and Balance Sheet line items)</li>
              <li>Valuation methodology (RIV for banks, DCF for others)</li>
            </ul>
            <p className="mt-4">
              Adding a new sector file automatically enables support for that sector without code changes.
              The AI will use these guidelines when generating financial models and investment theses.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
