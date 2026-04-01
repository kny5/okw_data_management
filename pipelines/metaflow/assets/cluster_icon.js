function createClusterIcon (cluster) {
  // 1. Define the colors array inside so it is always accessible
  const CLUSTER_COLORS = [
    '#1f8fff', '#2757ff', '#3d30ff', '#7d38ff', '#b841ff',
    '#ee49ff', '#ff52de', '#ff5ab1', '#ff6389', '#ff706b'
  ]

  // 2. Define the helper function inside so Leaflet can use it
  function getLogarithmicStyles (childCount, colors) {
    if (childCount <= 1) {
      return { text: '', color: colors[0], size: 20 }
    }

    const maxIndex = colors.length - 1
    const logVal = Math.log(childCount)
    const logMax = Math.log(1000)

    let index = Math.floor((logVal / logMax) * maxIndex)
    index = Math.min(Math.max(index, 1), maxIndex)

    let calculatedSize = 25 + Math.floor((logVal / logMax) * 20)
    calculatedSize = Math.min(Math.max(calculatedSize, 25), 45)

    return {
      text: childCount.toString(),
      color: colors[index],
      size: calculatedSize
    }
  }

  // 3. Execute the actual Leaflet Cluster logic
  const childCount = cluster.getChildCount()
  const opacity = 0.8

  let { text, color, size } = getLogarithmicStyles(childCount, CLUSTER_COLORS)

  if (childCount > 1) {
    text = `<span style="font-family: 'Fira Mono', monospace; font-weight: 500; font-style: normal; color: #fdfcad">${text}</span>`
  }

  // 4. Return the visual Leaflet icon
  return new L.DivIcon({
    html: `
            <div style="background-color:${color}; 
                height:${size}px; 
                width:${size}px; 
                opacity:${opacity}; 
                border-radius: 10%; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                text-align: center;
                box-shadow: 0 0 5px rgba(0,0,0,0.2);">
                ${text}
            </div>`,
    className: '',
    iconSize: new L.Point(size, size)
  })
}
