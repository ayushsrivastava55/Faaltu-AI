import { useState } from 'react';
import { FaThumbsUp, FaThumbsDown, FaChevronDown, FaChevronUp } from 'react-icons/fa';
import { cn } from '@/utils/cn';
import apiService from '@/services/api';

interface QueryResultProps {
  response: string;
  queryId?: string;
  contextUsed?: string[];
  domainsSearched?: string[];
  onFeedbackSubmitted?: (isHelpful: boolean) => void;
}

export default function QueryResult({
  response,
  queryId,
  contextUsed = [],
  domainsSearched = [],
  onFeedbackSubmitted
}: QueryResultProps) {
  const [feedback, setFeedback] = useState('');
  const [isHelpful, setIsHelpful] = useState<boolean | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [isFeedbackSubmitted, setIsFeedbackSubmitted] = useState(false);

  const handleFeedbackSubmit = async () => {
    if (queryId && isHelpful !== null) {
      try {
        await apiService.submitFeedback(queryId, feedback, isHelpful);
        setIsFeedbackSubmitted(true);
        if (onFeedbackSubmitted) {
          onFeedbackSubmitted(isHelpful);
        }
      } catch (error) {
        console.error('Error submitting feedback:', error);
      }
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 my-4">
      <div className="prose max-w-none">
        {response.split('\n').map((paragraph, idx) => (
          <p key={idx}>{paragraph}</p>
        ))}
      </div>

      {/* Details accordion */}
      <div className="mt-6 border-t pt-4">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="flex items-center text-sm text-gray-600 hover:text-gray-900"
        >
          {showDetails ? (
            <>
              <FaChevronUp className="mr-2" />
              Hide details
            </>
          ) : (
            <>
              <FaChevronDown className="mr-2" />
              Show details
            </>
          )}
        </button>

        {showDetails && (
          <div className="mt-4 text-sm">
            {domainsSearched.length > 0 && (
              <div className="mb-3">
                <h4 className="font-semibold text-gray-700">Knowledge domains searched:</h4>
                <div className="flex flex-wrap gap-2 mt-1">
                  {domainsSearched.map((domain, idx) => (
                    <span 
                      key={idx}
                      className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs"
                    >
                      {domain}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {contextUsed.length > 0 && (
              <div>
                <h4 className="font-semibold text-gray-700">Knowledge used:</h4>
                <ul className="list-disc pl-5 mt-1 space-y-1 text-gray-600">
                  {contextUsed.map((fact, idx) => (
                    <li key={idx}>{fact}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Feedback section */}
      {!isFeedbackSubmitted ? (
        <div className="mt-6 border-t pt-4">
          <h4 className="font-semibold text-gray-700 mb-2">Was this response helpful?</h4>
          
          <div className="flex gap-4 mb-3">
            <button
              onClick={() => setIsHelpful(true)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-full border",
                isHelpful === true
                  ? "bg-green-100 border-green-300 text-green-700"
                  : "border-gray-300 hover:bg-gray-50"
              )}
            >
              <FaThumbsUp />
              Yes
            </button>
            
            <button
              onClick={() => setIsHelpful(false)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-full border",
                isHelpful === false
                  ? "bg-red-100 border-red-300 text-red-700"
                  : "border-gray-300 hover:bg-gray-50"
              )}
            >
              <FaThumbsDown />
              No
            </button>
          </div>
          
          {isHelpful !== null && (
            <>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder={isHelpful ? "What did you find helpful?" : "How can we improve?"}
                className="w-full p-3 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                rows={3}
              />
              
              <button
                onClick={handleFeedbackSubmit}
                className="mt-3 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
              >
                Submit Feedback
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="mt-6 border-t pt-4 text-green-600">
          Thank you for your feedback!
        </div>
      )}
    </div>
  );
}
