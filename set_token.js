// Quick script to set john.doe token for testing
// Run this in the browser console (F12) when on localhost:3000

localStorage.setItem('token', '4067551d35f3d8fc08a9fa291f4f9d72fb70fdd7');
console.log('Token set for john.doe - refresh the page to see the dashboard');

// Alternatively, refresh the page automatically
window.location.reload();
