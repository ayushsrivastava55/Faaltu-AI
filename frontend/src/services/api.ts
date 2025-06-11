import axios from 'axios';

// Define the API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Define response types
export interface QueryResponse {
  response: string;
  requires_clarification?: boolean;
  clarification_questions?: string[];
  context_used?: string[];
  domains_searched?: string[];
}

export interface AnalysisResponse {
  is_ambiguous: boolean;
  has_multiple_intents: boolean;
  interpretations: string[];
  intents: string[];
  clarification_questions: string[];
  domains: string[];
}

export interface CommunityResponse {
  communities: {
    id: string;
    summary: string;
    size: number;
  }[];
}

// API service
export const apiService = {
  // Transcribe audio using backend service
  async transcribeAudio(audioFile: File): Promise<{ text: string; confidence: number }> {
    const formData = new FormData();
    formData.append('audio', audioFile);
    
    const response = await api.post('/transcribe/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },
  
  // Process query using advanced features
  async processQuery(query: string): Promise<QueryResponse> {
    const response = await api.post('/advanced-query/', { query });
    return response.data;
  },
  
  // Analyze query
  async analyzeQuery(query: string): Promise<AnalysisResponse> {
    const response = await api.post('/analyze-query/', { query });
    return response.data;
  },
  
  // Get community summaries
  async getCommunities(limit: number = 5): Promise<CommunityResponse> {
    const response = await api.get(`/community-summaries/?limit=${limit}`);
    return response.data;
  },
  
  // Advanced search
  async advancedSearch(
    query: string, 
    domain?: string, 
    limit: number = 10,
    searchType: 'hybrid' | 'semantic' | 'keyword' = 'hybrid'
  ) {
    const response = await api.post('/advanced-search/', {
      query,
      domain,
      limit,
      search_type: searchType,
    });
    return response.data;
  },
  
  // Submit feedback
  async submitFeedback(queryId: string, feedback: string, isHelpful: boolean) {
    const response = await api.post('/feedback/', {
      query_id: queryId,
      feedback,
      is_helpful: isHelpful,
    });
    return response.data;
  },
  
  // Build communities
  async buildCommunities() {
    const response = await api.post('/build-communities/');
    return response.data;
  },
};

export default apiService;
