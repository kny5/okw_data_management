function createMarker (row) {
  const marker = L.marker(new L.LatLng(row[0], row[1]))
  const popup = L.popup({ maxWidth: '300' })
  // const name = { text: row[2] }
  const url = { text: row[3] }
  const uid = { text: row[4] }

  const mytext = $(`<div id='pop_content' class='pop_custom' style='width: 100.0%; height: 100.0%;'>
                        <a href="${url.text}" target="_blank"><strong>${uid.text}</strong></a>
                    </div>`)[0]

  popup.setContent(mytext)
  marker.bindPopup(popup)
  return marker
};

// <a href="${url.text}" target="_blank"><strong>${name.text}</strong></a>
