import React, { useState } from 'react';

const AssistantForm = () => {
  const [query, setQuery] = useState('');  // State to store user input
  const [response, setResponse] = useState('');  // State to store assistant's response

  const submitQuery = async () => {
    const res = await fetch('http://localhost:5000/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),  // Sending user input (query) to the backend
    });
    const data = await res.json();  // Receiving the assistant's response
    setResponse(data.response);  // Updating the state to display the response
  };

  return (
    <div>
      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Enter your query"
      />
      <button onClick={submitQuery}>Submit</button>

      {/* Displaying assistant's response */}
      <div>{response}</div>
    </div>
  );
};

export default AssistantForm;
