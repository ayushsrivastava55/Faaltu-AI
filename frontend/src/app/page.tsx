"use client";

import { useState, useEffect } from 'react';
import Image from 'next/image';
import VoiceRecorder from '@/components/VoiceRecorder';
import QueryResult from '@/components/QueryResult';
import ClarificationQuestions from '@/components/ClarificationQuestions';
import Chat from '@/components/Chat';
import { TranscriptionResult } from '@/utils/whisper';
import apiService from '@/services/api';
import { FaMicrophone, FaRobot, FaInfoCircle, FaSpinner } from 'react-icons/fa';

export default function Home() {
  const [transcription, setTranscription] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentQuery, setCurrentQuery] = useState('');
  const [queryResult, setQueryResult] = useState<any>(null);
  const [clarificationQuestions, setClarificationQuestions] = useState<string[]>([]);
  const [requiresClarification, setRequiresClarification] = useState(false);
  const [queryHistory, setQueryHistory] = useState<Array<{query: string; result: any}>>([]);
  const [communitySummaries, setCommunitySummaries] = useState<Array<{id: string; summary: string; size: number}>>([]);
  const [isLoadingCommunities, setIsLoadingCommunities] = useState(false);

  // Fetch community summaries on load
  useEffect(() => {
    const fetchCommunities = async () => {
      try {
        setIsLoadingCommunities(true);
        const response = await apiService.getCommunities(3);
        setCommunitySummaries(response.communities);
      } catch (error) {
        console.error('Error fetching communities:', error);
      } finally {
        setIsLoadingCommunities(false);
      }
    };

    fetchCommunities();
  }, []);

  const handleTranscriptionComplete = async (result: TranscriptionResult) => {
    if (result.text) {
      setTranscription(result.text);
      setCurrentQuery(result.text);
      await processQuery(result.text);
    } else if (result.error) {
      setQueryResult({
        response: `Error during transcription: ${result.error}`,
        requires_clarification: false
      });
    }
  };

  const processQuery = async (query: string) => {
    try {
      setIsProcessing(true);
      const result = await apiService.processQuery(query);
      
      setQueryResult(result);
      setRequiresClarification(result.requires_clarification || false);
      
      if (result.requires_clarification && result.clarification_questions) {
        setClarificationQuestions(result.clarification_questions);
      } else {
        setClarificationQuestions([]);
        // Add to history if not requiring clarification
        setQueryHistory(prev => [...prev, { query, result }]);
      }
    } catch (error) {
      console.error('Error processing query:', error);
      setQueryResult({
        response: 'Sorry, there was an error processing your query. Please try again.',
        requires_clarification: false
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClarificationProvided = async (clarification: string) => {
    // Combine original query with clarification
    const clarifiedQuery = `${currentQuery} (Clarification: ${clarification})`;
    setCurrentQuery(clarifiedQuery);
    setRequiresClarification(false);
    await processQuery(clarifiedQuery);
  };

  const handleTextInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setTranscription(e.target.value);
  };

  const handleTextInputSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (transcription.trim()) {
      setCurrentQuery(transcription);
      await processQuery(transcription);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="bg-gradient-to-r from-purple-900 to-indigo-900 shadow-lg border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex items-center justify-between">
          <div className="flex items-center">
            <FaRobot className="text-purple-300 text-3xl mr-3" />
            <h1 className="text-xl font-bold text-white">FinMate AI Assistant</h1>
          </div>
          <div className="text-sm text-purple-200">Powered by Graphiti Knowledge Graphs</div>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content area */}
          <div className="lg:col-span-2 space-y-6">
            {/* Voice recorder */}
            <div className="bg-gray-900 rounded-lg shadow-lg p-6 border border-gray-800">
              <h2 className="text-lg font-semibold mb-4 flex items-center text-purple-300">
                <FaMicrophone className="text-purple-400 mr-2" />
                Voice Input
              </h2>
              
              <VoiceRecorder onTranscriptionComplete={handleTranscriptionComplete} />
            </div>
            
            {/* Chat Interface */}
            <Chat 
              onSendMessage={processQuery}
              isProcessing={isProcessing}
              assistantResponse={queryResult?.response}
              initialMessages={queryHistory.map(item => [
                {
                  id: `user-${item.query}`,
                  text: item.query,
                  sender: 'user' as const,
                  timestamp: new Date(Date.now() - 60000) // Approximate timestamp
                },
                {
                  id: `assistant-${item.query}`,
                  text: item.result.response,
                  sender: 'assistant' as const,
                  timestamp: new Date(Date.now() - 55000) // Approximate timestamp
                }
              ]).flat()}
            />
            
            {/* Clarification Questions */}
            {requiresClarification && clarificationQuestions.length > 0 && (
              <div className="bg-gray-900 rounded-lg shadow-lg p-6 border border-yellow-700">
                <ClarificationQuestions
                  questions={clarificationQuestions}
                  onClarificationProvided={handleClarificationProvided}
                />
              </div>
            )}
          </div>
          
          {/* Sidebar */}
          <div className="lg:col-span-1">
            {/* Knowledge graph communities */}
            <div className="bg-gray-900 rounded-lg shadow-lg p-6 mb-6 border border-gray-800">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-purple-300">Knowledge Communities</h2>
                {isLoadingCommunities && <FaSpinner className="animate-spin text-purple-400" />}
              </div>
              
              {communitySummaries.length > 0 ? (
                <div className="space-y-4">
                  {communitySummaries.map((community) => (
                    <div key={community.id} className="bg-gray-800 rounded-md p-3 border border-gray-700">
                      <div className="text-sm text-purple-300 mb-1">Community</div>
                      <p className="text-gray-300">{community.summary}</p>
                    </div>
                  ))}
                </div>
              ) : !isLoadingCommunities ? (
                <div className="text-gray-400 text-center py-4">
                  No community summaries available
                </div>
              ) : null}
            </div>
            
            {/* About section */}
            <div className="bg-gray-900 rounded-lg shadow-lg p-6 border border-gray-800">
              <h2 className="text-lg font-semibold mb-4 text-purple-300">About</h2>
              
              <div className="text-sm text-gray-300 space-y-2">
                <p>
                  This voice-to-text AI assistant uses advanced Graphiti knowledge graphs to provide 
                  contextually relevant answers to your questions.
                </p>
                <p>
                  Features include:
                </p>
                <ul className="list-disc pl-5 space-y-1">
                  <li>Voice input with faster-whisper</li>
                  <li>Knowledge graph integration</li>
                  <li>Multi-intent query handling</li>
                  <li>Temporal knowledge reasoning</li>
                  <li>Community-based knowledge organization</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}