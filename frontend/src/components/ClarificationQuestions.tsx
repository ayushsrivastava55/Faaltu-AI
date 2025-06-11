import { useState } from 'react';
import { FaQuestionCircle } from 'react-icons/fa';

interface ClarificationQuestionsProps {
  questions: string[];
  onClarificationProvided: (clarification: string) => void;
}

export default function ClarificationQuestions({
  questions,
  onClarificationProvided
}: ClarificationQuestionsProps) {
  const [clarification, setClarification] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (clarification.trim()) {
      onClarificationProvided(clarification);
    }
  };

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 my-4">
      <div className="flex items-start gap-3">
        <FaQuestionCircle className="text-amber-500 text-xl mt-1 flex-shrink-0" />
        
        <div className="flex-grow">
          <h3 className="font-semibold text-amber-800 mb-2">
            I need a bit more information
          </h3>
          
          <div className="mb-4">
            <p className="text-amber-700 mb-2">
              Your query could be interpreted in multiple ways. Please help me understand better:
            </p>
            
            <ul className="list-disc pl-5 space-y-1 text-amber-700">
              {questions.map((question, idx) => (
                <li key={idx}>{question}</li>
              ))}
            </ul>
          </div>
          
          <form onSubmit={handleSubmit}>
            <textarea
              value={clarification}
              onChange={(e) => setClarification(e.target.value)}
              placeholder="Please provide additional details..."
              className="w-full p-3 border border-amber-300 rounded-md focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none bg-white"
              rows={3}
              required
            />
            
            <button
              type="submit"
              className="mt-3 px-4 py-2 bg-amber-500 text-white rounded-md hover:bg-amber-600 transition-colors"
            >
              Submit Clarification
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
