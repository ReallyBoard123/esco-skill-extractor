"use client";

import { useMemo, useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";
import { Slider } from "@/components/ui/slider";
import { escoApi } from "@/lib/api";
import type { IntelligentAnalysisResults, GemmaSkillContext } from "@/lib/api";
import { useAnalysisStore } from "@/lib/analysisStore";
import { JobSearchSection } from "@/components/JobSearchSection";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const results = useAnalysisStore((state) => state.results);
  const setResults = useAnalysisStore((state) => state.setResults);
  const clearAllData = useAnalysisStore((state) => state.clearAllData);
  const [error, setError] = useState<string>("");
  const [skillThreshold, setSkillThreshold] = useState([0.68]);
  const [occupationThreshold, setOccupationThreshold] = useState([0.65]);
  const [maxResults, setMaxResults] = useState([15]);
  const skillContextMap = useMemo(() => {
    const map = new Map<string, GemmaSkillContext>();
    results?.skill_contexts?.forEach((context) => {
      if (context.skill_name) {
        map.set(context.skill_name.toLowerCase(), context);
      }
    });
    return map;
  }, [results]);

  const normalizeResponse = (data: any): IntelligentAnalysisResults => ({
    skills: data.extracted_skills ?? [],
    occupations: data.extracted_occupations ?? [],
    skill_contexts: data.skill_contexts ?? [],
    job_matches: data.current_job_matches ?? [],
    career_opportunities: data.career_opportunities ?? [],
    analysis_summary: data.analysis_summary,
    skill_gap_analysis: data.skill_gap_analysis,
    insights: data.insights,
    intelligent_recommendations: data.intelligent_recommendations ?? [],
    cv_sections: data.cv_sections,
    metadata: data.cv_metadata ?? data.file_info ?? data.metadata ?? {},
    location_hint: data.location_hint,
    city_suggestions: data.city_suggestions
  });

  const analyzePdf = async (selectedFile: File): Promise<IntelligentAnalysisResults> => {
    const formData = new FormData();
    formData.append("pdf", selectedFile);
    formData.append("detailed_analysis", "true");
    formData.append("skills_threshold", String(skillThreshold[0]));
    formData.append("occupations_threshold", String(occupationThreshold[0]));
    formData.append("max_results", String(maxResults[0]));

    const headers: Record<string, string> = {};
    if (typeof window !== "undefined" && window.location.hostname.includes("vercel.app")) {
      headers["skip_zrok_interstitial"] = "1";
      headers["User-Agent"] = "esco-frontend-client";
    }

    const response = await fetch(`${escoApi.getBaseUrl()}/analyze-cv-intelligent`, {
      method: "POST",
      body: formData,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
      throw new Error(`Failed to analyze PDF: ${errorData.detail || response.statusText}`);
    }

    const data = await response.json();

    console.log("Intelligent PDF Analysis Complete:", {
      filename: data.file_info?.filename,
      processingTime: data.analysis_summary?.processing_time,
      skillsFound: data.extracted_skills?.length ?? 0,
      occupationsFound: data.extracted_occupations?.length ?? 0,
      jobMatches: data.current_job_matches?.length ?? 0,
      careerOpportunities: data.career_opportunities?.length ?? 0
    });

    // Debug location extraction
    console.log("Location Analysis from Gemma:");
    console.log("location_hint:", data.location_hint);
    console.log("city_suggestions:", data.city_suggestions);

    return normalizeResponse(data);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type === "application/pdf") {
      setFile(selectedFile);
      setError("");
    } else {
      setFile(null);
      setError("Please select a valid PDF file");
    }
  };

  const handleSubmit = async () => {
    if (!file) {
      setError("Please upload a PDF to analyze");
      return;
    }

    setLoading(true);
    setError("");
    setResults(null);

    try {
      const analysisResults = await analyzePdf(file);
      setResults(analysisResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (results?.location_hint) {
      console.log("Detected location:", results.location_hint);
    }
  }, [results?.location_hint]);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto p-8">
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="flex flex-col gap-4 mb-6">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Upload a PDF CV
              </label>
              <div className="mt-2 flex items-center gap-4">
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileChange}
                  className="flex-1 text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
                {file && (
                  <span className="text-xs text-gray-600">
                    Selected: {file.name}
                  </span>
                )}
              </div>
            </div>

            <div className="flex justify-between">
              {results && (
                <Button
                  variant="outline"
                  onClick={() => {
                    clearAllData()
                    setFile(null)
                    setError("")
                  }}
                  className="text-red-600 border-red-300 hover:bg-red-50"
                >
                  Clear Analysis
                </Button>
              )}
              <Button
                onClick={handleSubmit}
                disabled={loading || !file}
                className="ml-auto"
              >
                {loading ? "Analyzing..." : "Analyze"}
              </Button>
            </div>
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
            <div className="mt-6">
              <label className="text-sm font-medium text-gray-700">
                Max Results: {maxResults[0]}
              </label>
              <Slider
                value={maxResults}
                onValueChange={setMaxResults}
                max={50}
                min={5}
                step={1}
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

        {results?.filter_summary && (
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Prefilter Summary</h2>
            <Accordion type="single" collapsible className="divide-y">
              <AccordionItem value="kept-sentences">
                <AccordionTrigger className="bg-green-50 text-green-900">
                  Professional sentences kept ({results.filter_summary.kept_sentences?.length || 0})
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-2">
                    {results.filter_summary.kept_sentences?.map((sentence, index) => (
                      <div key={`keep-${index}`} className="bg-green-50 border border-green-100 rounded p-3 text-sm text-green-900">
                        {sentence}
                      </div>
                    )) || <p className="text-gray-500 text-sm">No sentences kept</p>}
                  </div>
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="dropped-sentences">
                <AccordionTrigger className="bg-red-50 text-red-900">
                  Dropped as personal/hobby ({results.filter_summary.dropped_sentences?.length || 0})
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-2">
                    {results.filter_summary.dropped_sentences && results.filter_summary.dropped_sentences.length > 0 ? (
                      results.filter_summary.dropped_sentences.map((sentence, index) => (
                        <div key={`drop-${index}`} className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-900">
                          {sentence}
                        </div>
                      ))
                    ) : (
                      <p className="text-gray-500 text-sm">Nothing was filtered out</p>
                    )}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
            {results.filter_summary.notes && (
              <p className="text-xs text-gray-500 mt-4">
                {results.filter_summary.notes}
              </p>
            )}
          </div>
        )}

        {results?.location_hint?.city && (
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Detected Location</h2>
            <p className="text-sm text-gray-700">
              {results.location_hint.city}
              {results.location_hint.country ? `, ${results.location_hint.country}` : ""}
            </p>
            {results.location_hint.evidence && (
              <p className="text-xs text-gray-500 mt-2">Hinweis: {results.location_hint.evidence}</p>
            )}
          </div>
        )}

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
                      className="hover:shadow-md transition-shadow cursor-pointer border-l-4 border-l-blue-500"
                      onClick={() => window.open(skill.uri, '_blank')}
                    >
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base text-blue-800">
                          {skill.name}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                              {skill.similarity !== undefined ? `${Math.round(skill.similarity * 100)}% match` : "Match"}
                            </span>
                            {skill.categories && skill.categories.length > 0 && (
                              <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                                {skill.categories[0]}
                              </span>
                            )}
                          </div>
                          
                          {skill.matched_token && (
                            <div className="bg-blue-50 border border-blue-100 rounded p-2">
                              <p className="text-xs text-blue-600 mb-1">Matched text snippet:</p>
                              <p className="text-sm font-medium text-blue-900">
                                "...{skill.matched_token}..."
                              </p>
                            </div>
                          )}

                          {(() => {
                            const context = skillContextMap.get(skill.name.toLowerCase());
                            if (!context) return null;
                            return (
                              <div className="bg-indigo-50 border border-indigo-100 rounded p-2 space-y-1">
                                <p className="text-xs text-indigo-600 font-semibold">Gemma insight:</p>
                                {context.context_description && (
                                  <p className="text-sm text-indigo-900">{context.context_description}</p>
                                )}
                                <div className="flex flex-wrap gap-2 text-xs text-indigo-700">
                                  {context.used_in_role && (
                                    <span className="bg-white px-2 py-0.5 rounded border border-indigo-200">
                                      Role: {context.used_in_role}
                                    </span>
                                  )}
                                  {context.proficiency_level && (
                                    <span className="bg-white px-2 py-0.5 rounded border border-indigo-200 capitalize">
                                      Level: {context.proficiency_level}
                                    </span>
                                  )}
                                </div>
                              </div>
                            );
                          })()}
                          
                          {skill.skill_type && (
                            <p className="text-xs text-gray-500">
                              Type: {skill.skill_type.replace('skill/', '')}
                            </p>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No skills detected</p>
              )}
            </div>

            {results.career_role_insights && results.career_role_insights.length > 0 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">Role Fit Insights</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {results.career_role_insights.map((insight, index) => (
                    <Card key={index} className="border-l-4 border-l-indigo-500">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-lg text-indigo-800">{insight.role}</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <p className="text-sm text-gray-700">{insight.why_it_fits}</p>
                        {insight.skills_to_highlight && insight.skills_to_highlight.length > 0 && (
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Skills to highlight</p>
                            <div className="flex flex-wrap gap-1">
                              {insight.skills_to_highlight.slice(0, 5).map((skill, i) => (
                                <span key={i} className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {insight.gaps_to_address && insight.gaps_to_address.length > 0 && (
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Gaps to address</p>
                            <div className="flex flex-wrap gap-1">
                              {insight.gaps_to_address.slice(0, 5).map((gap, i) => (
                                <span key={i} className="text-xs bg-red-50 text-red-700 px-2 py-1 rounded">
                                  {gap}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                ESCO Occupations ({results.occupations.length})
              </h2>
              {results.occupations.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {results.occupations.map((occupation, index) => (
                    <Card 
                      key={index} 
                      className="hover:shadow-md transition-shadow cursor-pointer border-l-4 border-l-green-500"
                      onClick={() => window.open(occupation.uri, '_blank')}
                    >
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base text-green-800">
                          {occupation.name}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                              {occupation.similarity !== undefined ? `${Math.round(occupation.similarity * 100)}% match` : "Match"}
                            </span>
                              {occupation.iscoGroup && (
                                <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                                  ISCO: {occupation.iscoGroup}
                                </span>
                              )}
                          </div>
                          
                          {occupation.matched_token && (
                            <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
                              <p className="text-xs text-gray-600 mb-1">Found in your CV:</p>
                              <p className="text-sm font-medium text-gray-800">
                                "...{occupation.matched_token}..."
                              </p>
                            </div>
                          )}
                          
                          {occupation.description && (
                            <p className="text-xs text-gray-600 line-clamp-2">
                              {occupation.description}
                            </p>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No occupations detected</p>
              )}
            </div>


            {/* NEW: Career Opportunities Section */}
            {results.career_opportunities && results.career_opportunities.length > 0 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  🚀 Career Opportunities ({results.career_opportunities.length})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {results.career_opportunities.slice(0, 4).map((opportunity, index) => (
                    <Card key={index} className="hover:shadow-md transition-shadow border-l-4 border-l-purple-500">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-lg text-purple-800">
                          {opportunity.job.name}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-3">
                          <div className="flex justify-between items-center">
                            <span className="text-sm bg-purple-100 text-purple-700 px-3 py-1 rounded-full font-medium">
                              {opportunity.effort_level} effort
                            </span>
                            <span className="text-xs text-gray-600">
                              {opportunity.estimated_time}
                            </span>
                          </div>
                          
                          {opportunity.skills_to_gain && opportunity.skills_to_gain.length > 0 && (
                            <div>
                              <p className="text-xs text-gray-600 mb-1">Skills to gain:</p>
                              <div className="flex flex-wrap gap-1">
                                {opportunity.skills_to_gain.slice(0, 4).map((skill, i) => (
                                  <span key={i} className="text-xs bg-yellow-50 text-yellow-700 px-2 py-1 rounded">
                                    {skill}
                                  </span>
                                ))}
                                {opportunity.skills_to_gain.length > 4 && (
                                  <span className="text-xs text-gray-500">
                                    +{opportunity.skills_to_gain.length - 4} more
                                  </span>
                                )}
                              </div>
                            </div>
                          )}
                          
                          {opportunity.category_focus && opportunity.category_focus.length > 0 && (
                            <div>
                              <p className="text-xs text-gray-600 mb-1">Focus areas:</p>
                              <div className="flex flex-wrap gap-1">
                                {opportunity.category_focus.map((category, i) => (
                                  <span key={i} className="text-xs bg-indigo-50 text-indigo-700 px-2 py-1 rounded">
                                    {category}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* NEW: AI Recommendations Section */}
            {results.intelligent_recommendations && results.intelligent_recommendations.length > 0 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  💡 AI Career Recommendations
                </h2>
                <div className="space-y-3">
                  {results.intelligent_recommendations.map((rec, index) => (
                    <Card key={index} className="border-l-4 border-l-indigo-500 bg-indigo-50">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-lg text-indigo-900">
                          {rec.role || `Recommendation ${index + 1}`}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pt-0 space-y-3">
                        {rec.why_it_fits && (
                          <p className="text-sm text-gray-800">{rec.why_it_fits}</p>
                        )}
                        {rec.skills_to_highlight && rec.skills_to_highlight.length > 0 && (
                          <div>
                            <p className="text-xs text-gray-600 mb-1">Leverage these strengths:</p>
                            <div className="flex flex-wrap gap-1">
                              {rec.skills_to_highlight.slice(0, 5).map((skill, i) => (
                                <span key={i} className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {rec.recommended_actions && rec.recommended_actions.length > 0 && (
                          <div>
                            <p className="text-xs text-gray-600 mb-1">Next actions:</p>
                            <ul className="list-disc pl-5 text-sm text-gray-700 space-y-1">
                              {rec.recommended_actions.slice(0, 3).map((action, i) => (
                                <li key={i}>{action}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {rec.gaps_to_address && rec.gaps_to_address.length > 0 && (
                          <div>
                            <p className="text-xs text-gray-600 mb-1">Skills to build:</p>
                            <div className="flex flex-wrap gap-1">
                              {rec.gaps_to_address.slice(0, 4).map((gap, i) => (
                                <span key={i} className="text-xs bg-red-50 text-red-700 px-2 py-1 rounded">
                                  {gap}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}
            
            {/* Job Search Integration */}
            <JobSearchSection />
          </div>
        )}
      </div>
    </div>
  );
}
