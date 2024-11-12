// let recognition;
//         const transcriptElement = document.getElementById('transcript');
//         const startButton = document.getElementById('start-btn');
//         const stopButton = document.getElementById('stop-btn');

//         if ('webkitSpeechRecognition' in window) {
//             recognition = new webkitSpeechRecognition();
//             recognition.continuous = false;
//             recognition.interimResults = false;

//             recognition.onstart = function() {
//                 startButton.style.display = 'none';
//                 stopButton.style.display = 'inline';
//             };

//             recognition.onresult = function(event) {
//                 const userInput = event.results[0][0].transcript;
//                 transcriptElement.innerText = userInput;

//                 fetch('/process_speech/', {
//                     method: 'POST',
//                     headers: {
//                         'Content-Type': 'application/json',
//                         'X-CSRFToken': getCookie('csrftoken')
//                     },
//                     body: JSON.stringify({ speech: userInput })
//                 })
//                 .then(response => response.json())
//                 .then(data => {
//                     speakResponse(data.response);
//                 });
//             };

//             recognition.onend = function() {
//                 startButton.style.display = 'inline';
//                 stopButton.style.display = 'none';
//             };

//             startButton.onclick = function() {
//                 recognition.start();
//             };

//             stopButton.onclick = function() {
//                 recognition.stop();
//             };
//         } else {
//             alert('Your browser does not support speech recognition.');
//         }

//         function getCookie(name) {
//             let cookieValue = null;
//             if (document.cookie && document.cookie !== '') {
//                 const cookies = document.cookie.split(';');
//                 for (let i = 0; i < cookies.length; i++) {
//                     const cookie = cookies[i].trim();
//                     if (cookie.substring(0, name.length + 1) === (name + '=')) {
//                         cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
//                         break;
//                     }
//                 }
//             }
//             return cookieValue;
//         }

//         function speakResponse(responseText) {
//             const utterance = new SpeechSynthesisUtterance(responseText);
//             window.speechSynthesis.speak(utterance);
//         }