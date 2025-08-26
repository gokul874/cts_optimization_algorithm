# Combined Flask Application

This project combines two Flask applications: a member functionality and an admin functionality. The member section allows users to interact with member-specific features, while the admin section provides tools for managing and analyzing data.

## Project Structure

```
combined-flask-app
├── app.py
├── requirements.txt
├── instance
│   └── provider_network.db
├── member
│   ├── data_processor.py
│   ├── main.py
│   ├── attached_assets
│   │   └── Last provider data.csv
│   ├── static
│   │   ├── script.js
│   │   └── style.css
│   └── templates
│       └── index.html
├── admin
│   ├── main.py
│   ├── models.py
│   ├── routes.py
│   ├── uploads
│   ├── static
│   │   ├── css
│   │   │   └── custom.css
│   │   └── js
│   │       ├── dashboard.js
│   │       ├── main.js
│   │       └── visualization.js
│   ├── templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── index.html
│   │   ├── upload.html
│   │   └── visualization.html
│   └── utils
│       ├── data_processor.py
│       ├── geospatial.py
│       └── optimizer.py
├── pyproject.toml
└── README.md
```

## Setup Instructions

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd combined-flask-app
   ```

2. **Install dependencies**:
   Ensure you have Python and pip installed, then run:
   ```
   pip install -r requirements.txt
   ```

3. **Run the application**:
   Start the Flask application by running:
   ```
   python app.py
   ```

4. **Access the application**:
   Open your web browser and navigate to `http://127.0.0.1:5000` to access the member section or the admin section as defined in the routes.

## Usage Guidelines

- The **member section** allows users to view and interact with member-specific data and functionalities.
- The **admin section** provides tools for managing data, including uploading files, viewing dashboards, and performing data analysis.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.