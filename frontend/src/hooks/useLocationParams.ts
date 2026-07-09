import { useSearchParams } from 'react-router-dom';

export function useLocationParams() {
  const [searchParams] = useSearchParams();
  const lat = parseFloat(searchParams.get('lat') || '20.59');
  const lng = parseFloat(searchParams.get('lng') || '78.96');
  const name = searchParams.get('name') || '';
  return { lat: isNaN(lat) ? 20.59 : lat, lng: isNaN(lng) ? 78.96 : lng, name };
}
