import { useState, useRef, useEffect } from 'react';
import { FaMicrophone, FaStop, FaSpinner } from 'react-icons/fa';
import { cn } from '@/utils/cn';
import { audioTranscriber, TranscriptionResult } from '@/utils/whisper';

interface VoiceRecorderProps {
  onTranscriptionComplete: (result: TranscriptionResult) => void;
  isProcessing?: boolean;
}

export default function VoiceRecorder({ 
  onTranscriptionComplete,
  isProcessing = false
}: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const [recordingTime, setRecordingTime] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize audio transcriber
  useEffect(() => {
    const initTranscriber = async () => {
      try {
        await audioTranscriber.initialize();
      } catch (error) {
        console.error('Failed to initialize audio transcriber:', error);
      }
    };
    
    initTranscriber();
    
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      audioChunksRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await transcribeAudio(audioBlob);
        
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsRecording(true);
      
      // Start timer
      setRecordingTime(0);
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
    } catch (error) {
      console.error('Error accessing microphone:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      // Stop timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const transcribeAudio = async (audioBlob: Blob) => {
    setIsTranscribing(true);
    try {
      const result = await audioTranscriber.transcribe(audioBlob);
      onTranscriptionComplete(result);
    } catch (error) {
      console.error('Error transcribing audio:', error);
      onTranscriptionComplete({
        text: '',
        confidence: 0,
        error: error instanceof Error ? error.message : String(error)
      });
    } finally {
      setIsTranscribing(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isTranscribing || isProcessing}
          className={cn(
            "w-16 h-16 rounded-full flex items-center justify-center transition-all",
            isRecording 
              ? "bg-red-500 hover:bg-red-600" 
              : "bg-blue-500 hover:bg-blue-600",
            (isTranscribing || isProcessing) && "opacity-50 cursor-not-allowed"
          )}
        >
          {isRecording ? (
            <FaStop className="text-white text-xl" />
          ) : isTranscribing || isProcessing ? (
            <FaSpinner className="text-white text-xl animate-spin" />
          ) : (
            <FaMicrophone className="text-white text-xl" />
          )}
        </button>
        
        {isRecording && (
          <span className="absolute -top-2 -right-2 bg-red-600 text-white text-xs px-2 py-1 rounded-full animate-pulse">
            REC
          </span>
        )}
      </div>
      
      {isRecording && (
        <div className="mt-2 text-sm font-mono">
          {formatTime(recordingTime)}
        </div>
      )}
      
      <div className="mt-2 text-sm text-gray-500">
        {isRecording 
          ? "Click to stop recording" 
          : isTranscribing 
            ? "Transcribing..." 
            : isProcessing 
              ? "Processing..." 
              : "Click to start recording"}
      </div>
    </div>
  );
}
