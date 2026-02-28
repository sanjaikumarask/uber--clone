export interface LatLng {
    latitude: number;
    longitude: number;
}

/**
 * Decodes an encoded polyline string into an array of LatLng objects.
 */
export function decodePolyline(str: string, precision: number = 5): LatLng[] {
    let index = 0;
    let lat = 0;
    let lng = 0;
    const coordinates: LatLng[] = [];
    let shift = 0;
    let result = 0;
    let byte: number | null = null;
    let latitude_change: number;
    let longitude_change: number;
    const factor = Math.pow(10, precision);

    while (index < str.length) {
        byte = null;
        shift = 0;
        result = 0;

        do {
            byte = str.charCodeAt(index++) - 63;
            result |= (byte & 0x1f) << shift;
            shift += 5;
        } while (byte >= 0x20);

        latitude_change = result & 1 ? ~(result >> 1) : result >> 1;

        shift = 0;
        result = 0;

        do {
            byte = str.charCodeAt(index++) - 63;
            result |= (byte & 0x1f) << shift;
            shift += 5;
        } while (byte >= 0x20);

        longitude_change = result & 1 ? ~(result >> 1) : result >> 1;

        lat += latitude_change;
        lng += longitude_change;

        coordinates.push({
            latitude: lat / factor,
            longitude: lng / factor,
        });
    }

    return coordinates;
}
