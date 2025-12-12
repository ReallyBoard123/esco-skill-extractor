"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from "@/components/ui/pagination"
import { MapPin, Briefcase, ExternalLink, Loader2 } from "lucide-react"
import { useAnalysisStore } from "@/lib/analysisStore"
import { CityConfirmDialog } from "@/components/CityConfirmDialog"
// Note: German translations now come from backend Gemma analysis
// JobStore merged into AnalysisStore for better state management

export function JobSearchSection() {
  const {
    results,
    selectedRole,
    setSelectedRole,
    confirmedCity,
    setConfirmedCity,
    getRecommendedRoles,
    getBestLocationForJobSearch,
    jobSearchQuery,
    jobSearchLocation,
    jobSearchRadius,
    jobSearchLoading,
    jobSearchError,
    jobSearchResults,
    jobSearchTotal,
    searchJobs,
    clearJobResults,
    clearJobError
  } = useAnalysisStore()
  
  const [selectedGermanRole, setSelectedGermanRole] = useState<string>("")
  const [currentPage, setCurrentPage] = useState(1)
  const [showCityDialog, setShowCityDialog] = useState(false)
  const [pendingJobSearch, setPendingJobSearch] = useState<{role: string} | null>(null)
  const jobsPerPage = 10
  
  // Get roles with German translations from backend
  const getRecommendedRolesWithGerman = () => {
    const roles: Array<{english: string, german: string}> = []
    
    // Get from intelligent recommendations (with German translations)
    if (results?.intelligent_recommendations) {
      roles.push(...results.intelligent_recommendations.map(rec => ({
        english: rec.role,
        german: rec.german_role || rec.role
      })))
    }
    
    // Get from career role insights (with German translations)
    if (results?.career_role_insights) {
      roles.push(...results.career_role_insights.map(insight => ({
        english: insight.role,
        german: insight.german_role || insight.role
      })))
    }
    
    // Get from top career opportunities (fallback to English)
    if (results?.career_opportunities) {
      roles.push(...results.career_opportunities.slice(0, 3).map(opp => ({
        english: opp.job.name,
        german: opp.job.name // No German translation available for these
      })))
    }
    
    // Remove duplicates by English role name
    const uniqueRoles = roles.filter((role, index, self) => 
      index === self.findIndex(r => r.english === role.english)
    )
    
    return uniqueRoles.slice(0, 5)
  }
  
  const recommendedRoles = getRecommendedRolesWithGerman()
  const extractedLocation = getBestLocationForJobSearch()
  
  // Auto-select first recommended role and location when analysis completes
  useEffect(() => {
    if (recommendedRoles.length > 0 && !selectedRole) {
      const firstRole = recommendedRoles[0]
      setSelectedRole(firstRole.english)
      setSelectedGermanRole(firstRole.german)
    }
  }, [recommendedRoles, selectedRole, setSelectedRole])
  
  const handleRoleSelect = (englishRole: string, germanRole: string) => {
    setSelectedRole(englishRole)
    setSelectedGermanRole(germanRole)
    setCurrentPage(1) // Reset to first page
    clearJobResults()
    clearJobError()
  }
  
  const handleJobSearch = async () => {
    console.log("handleJobSearch called")
    console.log("selectedGermanRole:", selectedGermanRole)
    console.log("confirmedCity:", confirmedCity)
    
    if (!selectedGermanRole) {
      console.log("No German role selected, returning")
      return
    }
    
    // Check if user already confirmed a city
    if (confirmedCity) {
      // Use already confirmed city, skip dialog
      console.log(`Using already confirmed city: ${confirmedCity}`)
      console.log("About to call searchJobs with:", selectedGermanRole, confirmedCity, jobSearchRadius)
      await searchJobs(selectedGermanRole, confirmedCity, jobSearchRadius)
      console.log("searchJobs completed")
    } else {
      // Show city confirmation dialog for first time
      console.log("Showing city confirmation dialog")
      setPendingJobSearch({ role: selectedGermanRole })
      setShowCityDialog(true)
    }
  }
  
  const handleCityConfirm = async (city: string) => {
    // Save confirmed city to Zustand
    setConfirmedCity(city)
    
    // Perform job search if there's a pending search
    if (pendingJobSearch) {
      await searchJobs(pendingJobSearch.role, city, jobSearchRadius)
      setPendingJobSearch(null)
    }
    
    // Close dialog
    setShowCityDialog(false)
  }
  
  const handleCityCancel = () => {
    setPendingJobSearch(null)
    setShowCityDialog(false)
  }
  
  // No auto-search - user must confirm city first
  
  if (!results || recommendedRoles.length === 0) {
    return null
  }
  
  return (
    <div className="space-y-6">
      <Card className="border-l-4 border-l-green-500">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-green-800">
            <Briefcase className="w-5 h-5" />
            Job Search in Deutschland
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          
          {/* Role Selection */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Select a role to search for jobs:
            </h4>
            <div className="flex flex-wrap gap-2">
              {recommendedRoles.map((roleItem, index) => {
                const isSelected = selectedRole === roleItem.english
                
                return (
                  <button
                    key={index}
                    onClick={() => handleRoleSelect(roleItem.english, roleItem.german)}
                    className={`px-3 py-2 rounded-lg border text-sm transition-all ${
                      isSelected
                        ? "bg-green-100 border-green-300 text-green-800 font-medium"
                        : "bg-white border-gray-300 text-gray-700 hover:border-green-300"
                    }`}
                  >
                    <div className="text-left">
                      <div className={isSelected ? "font-medium" : ""}>{roleItem.english}</div>
                      <div className="text-xs text-gray-500">{roleItem.german}</div>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
          
          {/* Search Button */}
          {selectedRole && (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <div className="text-sm text-gray-600">
                  Search for: <span className="font-medium">{selectedGermanRole}</span>
                  {confirmedCity && (
                    <span> in <span className="font-medium">{confirmedCity}</span></span>
                  )}
                </div>
                <div className="flex gap-2">
                  {confirmedCity && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowCityDialog(true)}
                      className="text-xs"
                    >
                      Change City
                    </Button>
                  )}
                  <Button 
                    onClick={handleJobSearch}
                    disabled={jobSearchLoading || !selectedGermanRole}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {jobSearchLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Searching...
                      </>
                    ) : (
                      <>
                        <Briefcase className="w-4 h-4 mr-2" />
                        Find Jobs
                      </>
                    )}
                  </Button>
                </div>
              </div>
              
              {!confirmedCity && (
                <div className="text-xs text-gray-500 bg-blue-50 border border-blue-200 rounded p-2">
                  💡 First job search will ask you to confirm your city location
                </div>
              )}
            </div>
          )}
          
          {/* Error Display */}
          {jobSearchError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
              Error: {jobSearchError}
            </div>
          )}
          
          {/* Results Summary */}
          {jobSearchResults.length > 0 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <p className="text-sm text-green-800 font-medium">
                Found {jobSearchTotal} jobs for "{selectedGermanRole}"
                {extractedLocation && ` in ${extractedLocation}`}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
      
      {/* Job Results */}
      {jobSearchResults.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg text-gray-900">
              Job Results ({jobSearchTotal})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {jobSearchResults
                .slice((currentPage - 1) * jobsPerPage, currentPage * jobsPerPage)
                .map((job, index) => {
                // Construct job URL using reference number
                const jobUrl = job.refnr 
                  ? `https://www.arbeitsagentur.de/jobsuche/jobdetail/${job.refnr}`
                  : null
                
                return (
                  <div 
                    key={index} 
                    className={`border rounded-lg p-4 transition-all ${
                      jobUrl 
                        ? "hover:shadow-md cursor-pointer hover:bg-blue-50" 
                        : "hover:shadow-sm"
                    }`}
                    onClick={() => {
                      if (jobUrl) {
                        window.open(jobUrl, '_blank')
                      }
                    }}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-gray-900 hover:text-blue-700">
                            {job.titel || job.beruf}
                          </h3>
                          {jobUrl && (
                            <ExternalLink className="w-4 h-4 text-blue-500 opacity-60" />
                          )}
                        </div>
                        <p className="text-sm text-gray-600">{job.arbeitgeber}</p>
                      </div>
                      {job.arbeitsort?.ort && (
                        <Badge variant="outline" className="text-xs flex-shrink-0">
                          <MapPin className="w-3 h-3 mr-1" />
                          {job.arbeitsort.ort}
                        </Badge>
                      )}
                    </div>
                    
                    {job.arbeitsort?.strasse && (
                      <p className="text-xs text-gray-500 mb-1">{job.arbeitsort.strasse}</p>
                    )}
                    
                    <div className="flex justify-between items-center text-xs text-gray-500">
                      <span>Published: {job.aktuelleVeroeffentlichungsdatum}</span>
                      <span>Start: {job.eintrittsdatum}</span>
                    </div>
                    
                    {jobUrl && (
                      <div className="mt-2 text-xs text-blue-600 opacity-75">
                        Click to view on arbeitsagentur.de
                      </div>
                    )}
                  </div>
                )
              })}
              
              {/* Pagination Controls */}
              {jobSearchResults.length > jobsPerPage && (
                <div className="flex justify-center mt-6">
                  <Pagination>
                    <PaginationContent>
                      {currentPage > 1 && (
                        <PaginationItem>
                          <PaginationPrevious 
                            onClick={() => setCurrentPage(currentPage - 1)}
                            className="cursor-pointer"
                          />
                        </PaginationItem>
                      )}
                      
                      {Array.from({ length: Math.ceil(jobSearchResults.length / jobsPerPage) }, (_, i) => i + 1).map((pageNumber) => {
                        const totalPages = Math.ceil(jobSearchResults.length / jobsPerPage)
                        const showPage = pageNumber === 1 || 
                                        pageNumber === totalPages || 
                                        Math.abs(pageNumber - currentPage) <= 1
                        
                        if (!showPage) {
                          if ((pageNumber === 2 && currentPage > 4) || 
                              (pageNumber === totalPages - 1 && currentPage < totalPages - 3)) {
                            return (
                              <PaginationItem key={pageNumber}>
                                <span className="flex h-9 w-9 items-center justify-center">...</span>
                              </PaginationItem>
                            )
                          }
                          return null
                        }
                        
                        return (
                          <PaginationItem key={pageNumber}>
                            <PaginationLink
                              isActive={pageNumber === currentPage}
                              onClick={() => setCurrentPage(pageNumber)}
                              className="cursor-pointer"
                            >
                              {pageNumber}
                            </PaginationLink>
                          </PaginationItem>
                        )
                      })}
                      
                      {currentPage < Math.ceil(jobSearchResults.length / jobsPerPage) && (
                        <PaginationItem>
                          <PaginationNext 
                            onClick={() => setCurrentPage(currentPage + 1)}
                            className="cursor-pointer"
                          />
                        </PaginationItem>
                      )}
                    </PaginationContent>
                  </Pagination>
                </div>
              )}
              
              {/* Results summary */}
              <div className="text-center text-sm text-gray-500 mt-4">
                Showing {((currentPage - 1) * jobsPerPage) + 1} to {Math.min(currentPage * jobsPerPage, jobSearchResults.length)} of {jobSearchResults.length} jobs
              </div>
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* City Confirmation Dialog */}
      <CityConfirmDialog
        open={showCityDialog}
        onOpenChange={setShowCityDialog}
        detectedCity={results?.city_suggestions?.detected_current || extractedLocation}
        detectionReason={results?.city_suggestions?.detection_reason}
        confidence={results?.city_suggestions?.confidence}
        onConfirm={handleCityConfirm}
        onCancel={handleCityCancel}
      />
    </div>
  )
}