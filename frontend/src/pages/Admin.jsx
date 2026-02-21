import React, { useState, useEffect } from "react";
import { ShieldCheck, FileText, Plus, Edit, Trash2 } from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Admin() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [editing, setEditing] = useState(false);

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
      setLoading(false);
    }
  };

  const handleFileSelect = async (filename) => {
    try {
      const response = await axios.get(`${API}/admin/knowledge-files/${filename}`);
      setFileContent(response.data.content);
      setSelectedFile(filename);
      setEditing(false);
    } catch (err) {
      console.error("Failed to fetch file content:", err);
    }
  };

  const handleSave = async () => {
    try {
      await axios.put(`${API}/admin/knowledge-files/${selectedFile}`, fileContent, {
        headers: { 'Content-Type': 'text/plain' }
      });
      alert("File updated successfully!");
      setEditing(false);
      fetchFiles();
    } catch (err) {
      alert("Failed to update file");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <ShieldCheck className="w-8 h-8 text-indigo-400" />
            <h1 className="text-4xl font-bold text-white">Admin Panel</h1>
          </div>
          <p className="text-slate-400">Manage sector knowledge files</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* File List */}
          <div className="glass-card p-6 rounded-lg">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white">Knowledge Files</h2>
              <button className="text-indigo-400 hover:text-indigo-300">
                <Plus className="w-5 h-5" />
              </button>
            </div>
            
            {loading ? (
              <p className="text-slate-500">Loading...</p>
            ) : (
              <div className="space-y-2">
                {files.map((file) => (
                  <button
                    key={file.filename}
                    onClick={() => handleFileSelect(file.filename)}
                    className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors ${
                      selectedFile === file.filename
                        ? 'bg-indigo-600/20 border border-indigo-600'
                        : 'hover:bg-slate-800 border border-transparent'
                    }`}
                  >
                    <FileText className="w-5 h-5 text-indigo-400" />
                    <div className="flex-1 text-left">
                      <div className="text-white font-medium">{file.filename}</div>
                      <div className="text-xs text-slate-500">{file.sector}</div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Editor */}
          <div className="lg:col-span-2 glass-card p-6 rounded-lg">
            {selectedFile ? (
              <>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-white">{selectedFile}</h2>
                  <div className="flex gap-2">
                    {editing ? (
                      <>
                        <button
                          onClick={handleSave}
                          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditing(false)}
                          className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => setEditing(true)}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
                      >
                        <Edit className="w-4 h-4" />
                        Edit
                      </button>
                    )}
                  </div>
                </div>

                <textarea
                  value={fileContent}
                  onChange={(e) => setFileContent(e.target.value)}
                  disabled={!editing}
                  className="w-full h-[600px] bg-slate-900 border border-slate-700 rounded-lg p-4 text-slate-300 font-mono text-sm focus:outline-none focus:border-indigo-500 disabled:opacity-60"
                  style={{ resize: 'none' }}
                />
              </>
            ) : (
              <div className="flex items-center justify-center h-[600px]">
                <p className="text-slate-500">Select a file to view or edit</p>
              </div>
            )}
          </div>
        </div>

        {/* Info */}
        <div className="mt-8 glass-card p-6 rounded-lg">
          <h3 className="text-lg font-semibold text-white mb-3">About Knowledge Files</h3>
          <p className="text-slate-400 text-sm leading-relaxed">
            Knowledge files define how Mosaic models companies in each sector. Each .md file contains:
            sector classification rules, data sources, financial model structure, and valuation methodology.
            Adding a new sector file automatically enables support for that sector without code changes.
          </p>
        </div>
      </div>
    </div>
  );
}
