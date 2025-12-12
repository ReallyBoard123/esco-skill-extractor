import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { IntelligentAnalysisResults, CareerRoleInsight, LocationHint } from "@/lib/api"

export interface JobSearchResult {
  titel?: string
  beruf?: string
  arbeitgeber: string
  refnr?: string  // Reference number for constructing URL
  arbeitsort?: {
    ort?: string
    strasse?: string
  }
  aktuelleVeroeffentlichungsdatum: string
  eintrittsdatum: string
}

type AnalysisState = {
  // CV Analysis state (persisted)
  results: IntelligentAnalysisResults | null
  selectedRole: string | null
  extractedLocation: LocationHint | null
  confirmedCity: string | null
  
  // UI state (not persisted)
  isAnalyzing: boolean
  error: string | null
  
  // Job search state (not persisted - always fresh)
  jobSearchQuery: string
  jobSearchLocation?: string
  jobSearchRadius: number
  jobSearchLoading: boolean
  jobSearchError?: string
  jobSearchResults: JobSearchResult[]
  jobSearchTotal: number
  
  // CV Analysis actions
  setResults: (results: IntelligentAnalysisResults | null) => void
  setSelectedRole: (role: string | null) => void
  setConfirmedCity: (city: string | null) => void
  setIsAnalyzing: (analyzing: boolean) => void
  setError: (error: string | null) => void
  getRecommendedRoles: () => string[]
  getBestLocationForJobSearch: () => string | undefined
  
  // Job search actions
  searchJobs: (query: string, location?: string, radius?: number) => Promise<void>
  clearJobResults: () => void
  clearJobError: () => void
  clearAllData: () => void
}

export const useAnalysisStore = create<AnalysisState>()(
  persist(
    (set, get) => ({
      // CV Analysis state (persisted)
      results: null,
      selectedRole: null,
      extractedLocation: null,
      confirmedCity: null,
      
      // UI state (not persisted)
      isAnalyzing: false,
      error: null,
      
      // Job search state (not persisted)
      jobSearchQuery: "",
      jobSearchLocation: undefined,
      jobSearchRadius: 40,
      jobSearchLoading: false,
      jobSearchError: undefined,
      jobSearchResults: [],
      jobSearchTotal: 0,
      
      // CV Analysis actions
      setResults: (results) => {
        set({ 
          results,
          extractedLocation: results?.location_hint || null,
          error: null 
        })
      },
      
      setSelectedRole: (selectedRole) => set({ selectedRole }),
      setConfirmedCity: (confirmedCity) => set({ confirmedCity }),
      setIsAnalyzing: (isAnalyzing) => set({ isAnalyzing }),
      setError: (error) => set({ error }),
      
      getRecommendedRoles: () => {
        const state = get()
        const roles: string[] = []
        
        // Get from intelligent recommendations
        if (state.results?.intelligent_recommendations) {
          roles.push(...state.results.intelligent_recommendations.map(rec => rec.role))
        }
        
        // Get from career role insights
        if (state.results?.career_role_insights) {
          roles.push(...state.results.career_role_insights.map(insight => insight.role))
        }
        
        // Get from top career opportunities
        if (state.results?.career_opportunities) {
          roles.push(...state.results.career_opportunities.slice(0, 3).map(opp => opp.job.name))
        }
        
        // Remove duplicates and return top 5
        return [...new Set(roles)].slice(0, 5)
      },
      
      getBestLocationForJobSearch: () => {
        const state = get()
        
        // Priority 1: Use user confirmed city (highest priority)
        if (state.confirmedCity) {
          return state.confirmedCity
        }
        
        // Priority 2: Use new city_suggestions (AI detected)
        if (state.results?.city_suggestions) {
          const citySuggestions = state.results.city_suggestions
          
          // Prioritize detected_current (where they actually live/work)
          if (citySuggestions.detected_current && 
              citySuggestions.detected_current !== "null" && 
              citySuggestions.detected_current.trim() !== "" && 
              citySuggestions.confidence > 0.5) {
            return citySuggestions.detected_current
          }
          
          // Fallback to primary_city recommendation if no current location
          if (citySuggestions.primary_city && citySuggestions.confidence > 0.5) {
            return citySuggestions.primary_city
          }
        }
        
        // Priority 3: Fallback to old location_hint
        const location = state.extractedLocation || state.results?.location_hint
        if (location?.city && location.confidence && location.confidence > 0.3) {
          return location.city
        }
        
        return undefined
      },
      
      // Job search actions
      searchJobs: async (query: string, location?: string, radius: number = 40) => {
        set({ 
          jobSearchQuery: query,
          jobSearchLocation: location,
          jobSearchRadius: radius,
          jobSearchLoading: true,
          jobSearchError: undefined,
          jobSearchResults: []
        })
        
        try {
          const params = new URLSearchParams()
          params.set("was", query)
          if (location) params.set("wo", location)
          params.set("umkreis", radius.toString())
          params.set("size", "25")
          
          const response = await fetch(`/api/job-search?${params.toString()}`)
          
          if (!response.ok) {
            const errorText = await response.text()
            throw new Error(errorText || "Job search failed")
          }
          
          const data = await response.json()
          console.log("Job search API response:", data)
          const jobs = data.stellenangebote || []
          console.log("Jobs found:", jobs.length)
          
          // Sort jobs by publication date (newest first)
          const sortedJobs = jobs.sort((a: any, b: any) => {
            const dateA = new Date(a.aktuelleVeroeffentlichungsdatum || '1970-01-01').getTime()
            const dateB = new Date(b.aktuelleVeroeffentlichungsdatum || '1970-01-01').getTime()
            return dateB - dateA // Descending order (newest first)
          })
          
          console.log("Setting job search results:", {
            jobSearchResults: sortedJobs.length,
            jobSearchTotal: data.maxErgebnisse || jobs.length,
            jobSearchLoading: false
          })
          
          set({
            jobSearchResults: sortedJobs,
            jobSearchTotal: data.maxErgebnisse || jobs.length,
            jobSearchLoading: false,
            jobSearchError: undefined
          })
          
        } catch (error) {
          set({
            jobSearchLoading: false,
            jobSearchError: error instanceof Error ? error.message : "Unknown error occurred",
            jobSearchResults: [],
            jobSearchTotal: 0
          })
        }
      },
      
      clearJobResults: () => set({ 
        jobSearchResults: [], 
        jobSearchTotal: 0, 
        jobSearchError: undefined 
      }),
      
      clearJobError: () => set({ jobSearchError: undefined }),
      
      clearAllData: () => set({
        results: null,
        selectedRole: null,
        extractedLocation: null,
        confirmedCity: null,
        error: null,
        jobSearchQuery: "",
        jobSearchLocation: undefined,
        jobSearchResults: [],
        jobSearchTotal: 0,
        jobSearchError: undefined
      })
    }),
    {
      name: "esco-cv-analysis", // localStorage key
      partialize: (state) => ({
        // Only persist analysis results, not UI state or job search
        results: state.results,
        selectedRole: state.selectedRole,
        extractedLocation: state.extractedLocation,
        confirmedCity: state.confirmedCity
      }),
    }
  )
)
