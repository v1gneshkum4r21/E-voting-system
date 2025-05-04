# E-Voting System

A secure and user-friendly electronic voting system built with Flask and SQLite. This system offers comprehensive election management capabilities with role-based access controls and a modern, responsive UI design.

## Features

### User Authentication & Account Management
- Secure user registration with email & password
- Login/logout functionality
- Password hashing for security
- Forgot password & reset functionality
- Role-based access control (Admin, Voter, Candidate)
- User profile management
- Modern authentication UI with intuitive forms

### Voter Portal
- Dashboard showing active, upcoming, and past elections
- Real-time voting interface with live updates
- Statistics cards for quick overview of voting activity
- Visual representation of party distribution and popular candidates
- Interactive ballot system with candidate cards
- Mobile-responsive design
- Vote confirmation and receipt (reference ID)
- Comprehensive voting history view

### Candidate Portal
- Registration for elections with intuitive forms
- Modern dashboard with statistics and status overview
- Profile and candidacy management
- Enhanced candidacy display with manifesto support
- Status tracking (pending, approved, rejected)
- View elections participating in with detailed information

### Admin Portal
- System dashboard with comprehensive statistics
- User management (view/edit/delete)
- Candidate verification with approval workflow
- Election creation and management
- Modern table designs with enhanced usability
- Interactive results visualization
- Activity logs and reporting
- Results export in CSV format

### Ballot System
- Digital ballot creation
- Candidate listing with detailed profiles
- Visual candidate cards with photos/logos
- Secure, one-time vote validation
- Interactive voting experience

### Results & Analytics
- Automated vote tallying
- Live updating results with animations
- Visual representation with charts and progress bars
- Detailed breakdown of voting statistics
- Exportable reports
- Winner highlighting and vote distribution analysis

## UI Features

- Modern card-based design with subtle shadows
- Consistent color scheme and visual hierarchy
- Soft background colors for icons and visual elements
- Responsive layout that works on all devices
- Interactive elements with hover effects
- Clean typography and improved readability
- Status indicators with color-coded badges
- Progress bars and visual data representations
- Intuitive navigation and breadcrumbs

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/evoting-system.git
cd evoting-system
```

2. Create a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Run the application:
```
python app.py
```

5. Access the application at `http://localhost:5000`

## Default Admin Account

- Email: admin@evoting.com
- Password: admin123

## Project Structure

```
evoting-system/
├── app/
│   ├── controllers/        # Route handlers
│   ├── models/             # Database models
│   ├── static/             # CSS, JS, images
│   ├── templates/          # HTML templates
│   └── utils/              # Utility functions
├── database/               # SQLite database
├── app.py                  # Main application file
├── requirements.txt        # Dependencies
└── README.md               # Documentation
```

## Technologies Used

- **Backend**: Flask (Python)
- **Database**: SQLite3
- **Frontend**: Bootstrap 5, JavaScript, AJAX for real-time updates
- **UI Components**: Modern card-based layouts, interactive tables
- **Data Visualization**: Dynamic progress bars and charts
- **Security**: bcrypt for password hashing, CSRF protection

## License

This project is licensed under the MIT License - see the LICENSE file for details. 