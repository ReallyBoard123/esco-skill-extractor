"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { escoApi } from "@/lib/api";
import type { ExtractResults } from "@/lib/api";

type AnalysisResults = ExtractResults;

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<AnalysisResults | null>(null);
  const [error, setError] = useState<string>("");
  const [skillThreshold, setSkillThreshold] = useState([0.63]);
  const [occupationThreshold, setOccupationThreshold] = useState([0.60]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type === "application/pdf") {
      setFile(selectedFile);
      setError("");
    } else {
      setError("Please select a valid PDF file");
    }
  };

  const extractSkillsFromPDF = async (file: File): Promise<AnalysisResults> => {
    const formData = new FormData();
    formData.append("pdf", file);
    formData.append("skills_threshold", skillThreshold[0].toString());
    formData.append("occupations_threshold", occupationThreshold[0].toString());
    formData.append("rich_data", "true");
    formData.append("max_results", "100");

    // Call the Python backend for complete PDF processing
    const baseUrl = escoApi.getBaseUrl();
    const response = await fetch(`${baseUrl}/extract-pdf-skills`, {
      method: "POST",
      body: formData,
      headers: {
        'skip_zrok_interstitial': '1',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(`Failed to process PDF: ${errorData.detail || response.statusText}`);
    }

    const data = await response.json();
    
    console.log('PDF Processing Complete:', {
      filename: data.metadata?.filename,
      pages: data.metadata?.pages,
      textLength: data.metadata?.text_length,
      skillsFound: data.skills?.length ?? 0,
      occupationsFound: data.occupations?.length ?? 0,
    });
    
    return data;
  };

  const handleSubmit = async () => {
    if (!file) return;

    setLoading(true);
    setError("");
    setResults(null);

    try {
      const analysisResults = await extractSkillsFromPDF(file);
      setResults(analysisResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto p-8">
         <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="flex items-center gap-4 mb-6">
            <input 
              type="file" 
              accept=".pdf" 
              onChange={handleFileChange} 
              className="flex-1 text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            <Button onClick={handleSubmit} disabled={!file || loading}>
              {loading ? "Analyzing..." : "Extract"}
            </Button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Skill Threshold: {skillThreshold[0].toFixed(2)}
              </label>
              <Slider
                value={skillThreshold}
                onValueChange={setSkillThreshold}
                max={1}
                min={0}
                step={0.01}
                className="w-full"
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Occupation Threshold: {occupationThreshold[0].toFixed(2)}
              </label>
              <Slider
                value={occupationThreshold}
                onValueChange={setOccupationThreshold}
                max={1}
                min={0}
                step={0.01}
                className="w-full"
              />
            </div>
          </div>
          
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded">
              {error}
            </div>
          )}
        </div>

        {results && (
          <div className="space-y-8">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                ESCO Skills ({results.skills.length})
              </h2>
              {results.skills.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {results.skills.map((skill, index) => (
                    <Card 
                      key={index} 
                      className="hover:shadow-md transition-shadow cursor-pointer"
                      onClick={() => window.open(skill.uri, '_blank')}
                    >
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base text-blue-800">
                          {skill.name}
                        </CardTitle>
                      </CardHeader>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No skills detected</p>
              )}
            </div>

            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                ESCO Occupations ({results.occupations.length})
              </h2>
              {results.occupations.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {results.occupations.map((occupation, index) => (
                    <Card 
                      key={index} 
                      className="hover:shadow-md transition-shadow cursor-pointer"
                      onClick={() => window.open(occupation.uri, '_blank')}
                    >
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base text-green-800">
                          {occupation.name}
                        </CardTitle>
                      </CardHeader>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No occupations detected</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
