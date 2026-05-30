import React, { useState } from 'react';

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<{ text: string; sender: 'user' | 'bot' }[]>([]);
  const [inputValue, setInputValue] = useState('');

  const handleSendMessage = () => {
    if (inputValue.trim()) {
      setMessages([...messages, { text: inputValue, sender: 'user' }]);
      // Here you would typically send the message to the backend
      // and receive a response from the bot.
      // For now, we'll just simulate a bot response.
      setTimeout(() => {
        setMessages(prevMessages => [...prevMessages, { text: 'This is a response from the bot.', sender: 'bot' }]);
      }, 1000);
      setInputValue('');
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg">
      <div className="flex-1 overflow-y-auto p-6">
        {messages.map((message, index) => (
          <div key={index} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'} mb-4`}>
            <div className={`rounded-lg px-4 py-2 max-w-md ${message.sender === 'user' ? 'bg-blue-500 text-white' : 'bg-slate-200 text-slate-800'}`}>
              {message.text}
            </div>
          </div>
        ))}
      </div>
      <div className="p-4 border-t border-slate-200">
        <div className="flex items-center bg-slate-100 rounded-lg px-2">
          <input
            type="text"
            className="flex-1 border-none bg-transparent rounded-lg p-2 focus:outline-none"
            placeholder="Type your message..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
          />
          <button className="bg-blue-500 text-white rounded-lg px-4 py-2 m-2" onClick={handleSendMessage}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chat;
