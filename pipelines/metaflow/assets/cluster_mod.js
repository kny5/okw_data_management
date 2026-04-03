function createMarker(row) {
  // 1. Extract the raw row data
  const name = { text: row[2] };
  const source = { text: row[3] };
  const ext_url = { text: row[4] };
  const uid = { text: row[5] };
  const source_url = { text: row[6] };
  
  // 2. Define the source mappings
  const source_names = {
    "01": "",
    "02": "FABLABS.IO",
    "03": "BayArea MakerSpaces",
    "04": "Makerspaces in Libraries, Museums & Schools",
    "05": "",
    "06": "MAKE WORKS",
    "07": "OFFENE WERKSTAETTEN",
    "08": "UC Berkeley's Jacobs Institute for Design Innovation",
    "09": "HACKERSPACES.ORG",
    "10": "MAKERY",
    "11": "MAKERSPACE.COM",
    "12": "FIELD READY COVID RESPONSE",
  };

  // 3. Get the readable name (and provide a fallback just in case)
  const actualSourceName = source_names[source.text] || "Unknown Source";
  const link = source_url.text || ext_url.text 

  const href = link ? (link.text || link) : null;

  const titleHtml = href 
    ? `<a href="${href}" target="_blank"><strong>${uid.text || 'No UID Provided'}</strong></a>` 
    : `<strong>${uid?.text || uid}</strong>`;

  // const actualSourceName = source
  // 4. CREATE THE MARKER WITH THE CUSTOM SOURCE OPTION
  // This is the crucial step that allows our Chart script to read the source later
  
  const marker = L.marker(new L.LatLng(row[0], row[1]), { 
      customSource: actualSourceName 
  });

  // 5. Setup the popup


 const popup = L.popup({ maxWidth: '300' });
 const mytext = $(`<div id='pop_content' class='pop_custom' style='width: 100.0%; height: 100.0%;'>
                       ${titleHtml}<br>${name.text}<br>${actualSourceName}
                   </div>`)[0];

 popup.setContent(mytext);
 marker.bindPopup(popup);
return marker;
}

