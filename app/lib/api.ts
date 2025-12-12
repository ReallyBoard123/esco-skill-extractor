export interface SkillUsageBreakdown {
  essential: number;
  optional: number;
}

export interface SkillUsage {
  count: number;
  examples: string[];
  breakdown: SkillUsageBreakdown;
}

export interface RichSkill {
  name: string;
  uri: string;
  type?: string;
  reuseLevel?: string;
  description?: string;
  alternatives?: string[];
  categories?: string[];
  usedInOccupations?: SkillUsage;
  similarity?: number;
}

export interface OccupationSkillSet {
  essential: string[];
  optional: string[];
  totalEssential: number;
  totalOptional: number;
}

export interface RichOccupation {
  name: string;
  uri: string;
  iscoGroup?: string;
  description?: string;
  alternatives?: string[];
  requiredSkills?: OccupationSkillSet;
  skillCategories?: Record<string, number>;
  similarity?: number;
}

export interface ExtractionMetadata {
  processedText?: string;
  totalSkillsFound?: number;
  totalOccupationsFound?: number;
  processingTime?: string;
  thresholds?: {
    skills?: number;
    occupations?: number;
  };
}

export interface ExtractResults {
  skills: RichSkill[];
  occupations: RichOccupation[];
  metadata?: ExtractionMetadata;
}

export interface GemmaSkillContext {
  skill_name: string;
  proficiency_level?: string;
  years_experience?: string;
  context_description?: string;
  used_in_role?: string;
  industry_context?: string;
}

export interface IntelligentSkill extends RichSkill {
  matched_token?: string;
  skill_type?: string;
}

export interface IntelligentOccupation extends RichOccupation {
  matched_token?: string;
}

export interface FilterSummary {
  kept_sentences?: string[];
  dropped_sentences?: string[];
  notes?: string;
}

export interface JobMatch {
  name: string;
  match_score: number;
  matched_skills: string[];
  missing_essential: string[];
}

export interface CareerOpportunity {
  job: JobMatch;
  skills_to_gain: string[];
  effort_level: string;
  category_focus: string[];
  estimated_time: string;
}

export interface CareerRoleInsight {
  role: string;
  german_role?: string;
  why_it_fits: string;
  skills_to_highlight?: string[];
  gaps_to_address?: string[];
  recommended_actions?: string[];
}

export interface LocationHint {
  city?: string;
  country?: string;
  confidence?: number;
  evidence?: string;
}

export interface CitySuggestion {
  city: string;
  reason: string;
}

export interface CitySuggestions {
  primary_city: string;
  suggested_cities: CitySuggestion[];
  detected_current: string;
  confidence: number;
  detection_reason?: string;
}

export interface IntelligentAnalysisResults {
  skills: IntelligentSkill[];
  occupations: IntelligentOccupation[];
  skill_contexts?: GemmaSkillContext[];
  job_matches?: JobMatch[];
  career_opportunities?: CareerOpportunity[];
  analysis_summary?: Record<string, unknown>;
  skill_gap_analysis?: Record<string, unknown>;
  insights?: Record<string, unknown>;
  intelligent_recommendations?: CareerRoleInsight[];
  filter_summary?: FilterSummary;
  career_role_insights?: CareerRoleInsight[];
  cv_sections?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  location_hint?: LocationHint;
  city_suggestions?: CitySuggestions;
}

export interface HealthCheckResponse {
  status: string;
  model: string;
  device?: string;
  timestamp?: string;
}

class EscoApiService {
  private baseUrl: string;

  constructor() {
    if (typeof window !== 'undefined' && window.location.hostname.includes('vercel.app')) {
      this.baseUrl = 'https://skillextract.share.zrok.io';
    } else {
      this.baseUrl = 'http://localhost:9000';
    }
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    if (typeof window !== 'undefined' && window.location.hostname.includes('vercel.app')) {
      headers['skip_zrok_interstitial'] = '1';
      headers['User-Agent'] = 'esco-frontend-client';
    }
    
    return headers;
  }

  private async handleApiError(response: Response, operation: string): Promise<never> {
    let errorMessage = `${operation} failed: ${response.status} ${response.statusText}`;
    
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMessage = typeof errorData.detail === 'string' 
          ? errorData.detail 
          : errorData.detail.message || errorMessage;
      }
    } catch {
    }
    
    throw new Error(errorMessage);
  }

  async healthCheck(): Promise<HealthCheckResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/`, {
        headers: this.getHeaders(),
      });
      
      if (!response.ok) {
        await this.handleApiError(response, 'Health check');
      }
      
      return await response.json();
    } catch (error) {
      throw new Error(`Backend is not responding: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async analyzeTextIntelligent(
    text: string,
    skillThreshold?: number,
    occupationThreshold?: number,
    maxResults = 25
  ): Promise<IntelligentAnalysisResults> {
    try {
      const payload: Record<string, unknown> = {
        text,
        max_results: maxResults,
      };

      if (skillThreshold !== undefined) {
        payload.skills_threshold = skillThreshold;
      }

      if (occupationThreshold !== undefined) {
        payload.occupations_threshold = occupationThreshold;
      }

      const response = await fetch(`${this.baseUrl}/analyze-text-intelligent`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        await this.handleApiError(response, 'Intelligent text analysis');
      }

      return await response.json();
    } catch (error) {
      throw new Error(`Intelligent text analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

}

// Export singleton instance
export const escoApi = new EscoApiService();
