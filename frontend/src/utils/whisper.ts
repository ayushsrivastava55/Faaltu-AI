import axios from 'axios';

// Define the API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Define the types for our whisper transcription
export interface TranscriptionResult {
  text: string;
  confidence: number;
  language?: string;
  error?: string;
}

// Class to handle audio transcription using backend API
export class AudioTranscriber {
  private static instance: AudioTranscriber;
  private isInitialized: boolean = false;

  private constructor() {}

  public static getInstance(): AudioTranscriber {
    if (!AudioTranscriber.instance) {
      AudioTranscriber.instance = new AudioTranscriber();
    }
    return AudioTranscriber.instance;
  }

  public async initialize(): Promise<void> {
    if (this.isInitialized) return;
    
    try {
      // Check if the API is available
      await axios.get(`${API_BASE_URL}/health`);
      this.isInitialized = true;
    } catch (error) {
      console.error('Error connecting to transcription API:', error);
      throw error;
    }
  }

  public async transcribe(audioData: Blob): Promise<TranscriptionResult> {
    try {
      await this.initialize();

      // Create a FormData object to send the audio file
      const formData = new FormData();
      formData.append('file', audioData, 'audio.wav');

      // Send the audio to the backend for transcription
      const response = await axios.post(`${API_BASE_URL}/upload-audio/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      return {
        text: response.data.text,
        confidence: response.data.confidence,
      };
    } catch (error) {
      console.error('Error transcribing audio:', error);
      return {
        text: '',
        confidence: 0,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }
}

// Export a singleton instance
export const audioTranscriber = AudioTranscriber.getInstance();
