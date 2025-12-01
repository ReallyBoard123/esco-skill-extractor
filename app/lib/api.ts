interface EscoItem {
  id: string;
  description: string;
}

interface SkillExtractionRequest {
  texts: string[];
  threshold?: number;
}

interface OccupationExtractionRequest {
  texts: string[];
  threshold?: number;
}

interface SkillExtractionResponse {
  skills: string[][];
  threshold: number;
  model: string;
  timestamp: string;
}

interface OccupationExtractionResponse {
  occupations: string[][];
  threshold: number;
  model: string;
  timestamp: string;
}

interface HealthCheckResponse {
  status: string;
  model: string;
  device: string;
  timestamp: string;
}

interface ExtractResults {
  skills: EscoItem[];
  occupations: EscoItem[];
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

  async extractSkills(texts: string[], threshold?: number): Promise<SkillExtractionResponse> {
    try {
      const payload: SkillExtractionRequest = {
        texts,
        ...(threshold !== undefined && { threshold })
      };

      const response = await fetch(`${this.baseUrl}/extract-skills`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) {
        await this.handleApiError(response, 'Skill extraction');
      }
      
      return await response.json();
    } catch (error) {
      throw new Error(`Skill extraction failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async extractOccupations(texts: string[], threshold?: number): Promise<OccupationExtractionResponse> {
    try {
      const payload: OccupationExtractionRequest = {
        texts,
        ...(threshold !== undefined && { threshold })
      };

      const response = await fetch(`${this.baseUrl}/extract-occupations`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) {
        await this.handleApiError(response, 'Occupation extraction');
      }
      
      return await response.json();
    } catch (error) {
      throw new Error(`Occupation extraction failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async extractBoth(text: string, skillThreshold?: number, occupationThreshold?: number): Promise<ExtractResults> {
    try {
      const [skillsResponse, occupationsResponse] = await Promise.all([
        this.extractSkills([text], skillThreshold),
        this.extractOccupations([text], occupationThreshold),
      ]);

      const skillUrls = skillsResponse.skills[0] || [];
      const occupationUrls = occupationsResponse.occupations[0] || [];

      const decodedResults = await this.decodeEscoItems(skillUrls, occupationUrls);
      
      return decodedResults;
    } catch (error) {
      throw new Error(`Combined extraction failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private async decodeEscoItems(skillUrls: string[], occupationUrls: string[]): Promise<ExtractResults> {
    try {
      const response = await fetch('/api/decode-esco', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skills: skillUrls,
          occupations: occupationUrls,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to decode ESCO data');
      }

      const decodedData = await response.json();
      
      const uniqueSkills = decodedData.skills.filter((skill: EscoItem, index: number, arr: EscoItem[]) => 
        arr.findIndex(s => s.description.toLowerCase() === skill.description.toLowerCase()) === index
      );
      
      const uniqueOccupations = decodedData.occupations.filter((occupation: EscoItem, index: number, arr: EscoItem[]) => 
        arr.findIndex(o => o.description.toLowerCase() === occupation.description.toLowerCase()) === index
      );
      
      return {
        skills: uniqueSkills,
        occupations: uniqueOccupations,
      };
    } catch (error) {
      throw new Error(`Failed to decode ESCO data: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

}

// Export singleton instance
export const escoApi = new EscoApiService();

export type {
  EscoItem,
  SkillExtractionRequest,
  OccupationExtractionRequest,
  SkillExtractionResponse,
  OccupationExtractionResponse,
  HealthCheckResponse,
  ExtractResults
};