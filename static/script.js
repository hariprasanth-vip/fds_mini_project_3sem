// Function to load and display available halls based on the selected date
async function loadHalls() {
    const date = document.getElementById('bookingDate').value;
    const today = new Date().toISOString().split('T')[0];

    if (!date) {
        // If the date field is empty, do nothing or prompt the user.
        // We allow initial load to pass if date is set by DOMContentLoaded.
        return;
    }
    
    // இன்று அல்லது அதற்குப் பிறகு உள்ள தேதியை மட்டுமே அனுமதிக்கவும் (Only allow today or future dates)
    if (date < today) {
        alert('You cannot book a hall for a past date!');
        document.getElementById('bookingDate').value = today;
        return;
    }

    try {
        // API call to fetch halls with availability status for the given date
        const response = await axios.get(`/api/halls?date=${date}`);
        const halls = response.data;
        const container = document.getElementById('halls');
        container.innerHTML = '';

        if (halls.length === 0) {
            container.innerHTML = '<p class="info-msg">No halls found or unauthorized.</p>';
            return;
        }

        halls.forEach(h => {
            const div = document.createElement('div');
            div.className = h.available ? 'hall-card available' : 'hall-card booked';
            div.innerHTML = `
                <h3>${h.name}</h3>
                <p>Capacity: ${h.capacity}</p>
                <p>Status: <strong>${h.available ? '✅ Available' : '❌ Booked'}</strong></p>
                ${h.available ? `
                    <input type="number" id="att_${h.id}" placeholder="No. of attendees" min="1" max="${h.capacity}" value="1">
                    <button onclick="bookHall(${h.id}, '${date}', '${h.name}')">Book Now</button>
                ` : ''}
            `;
            container.appendChild(div);
        });
    } catch (error) {
        const errorMsg = error.response ? (error.response.data.error || 'Server error') : 'Network error.';
        alert(`Error loading halls: ${errorMsg}`);
        console.error(error);
    }
}

// Function to handle hall booking
async function bookHall(hallId, date, hallName) {
    const attendeesInput = document.getElementById(`att_${hallId}`);
    const attendees = attendeesInput.value;

    if (!attendees || attendees < 1) {
        alert('Please enter a valid number of attendees.');
        return;
    }

    try {
        const res = await axios.post('/api/book', { hall_id: hallId, date, attendees });
        
        // Successful booking message
        alert(`✅ Success: ${res.data.message}`);
        
        // Refresh the hall list to show the booked status instantly
        loadHalls(); 
    } catch (error) {
        // Handle server-side errors (e.g., already booked, capacity exceeded)
        const errorMsg = error.response ? (error.response.data.error || 'Server error') : 'Network error.';
        alert(`❌ Booking Failed: ${errorMsg}`);
        console.error(error);
    }
}

// Set default date and load halls on page load
// Indha function, page load aana udane inraiya thethiyai set panni, loadHalls-a call pannum
document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('bookingDate');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.min = today; 
        
        // Only set value if it's not already set (prevents clearing user input on refresh)
        if (!dateInput.value) {
            dateInput.value = today;
        }
        
        // Page load ஆனவுடன் இன்றைய தேதிக்கான தகவலைக் காட்டுகிறது
        loadHalls(); 
    }
});