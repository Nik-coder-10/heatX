import sys
sys.path.insert(0, '.')

# Check individual sub-routers
from app.api.v1.endpoints import satellite_image
print('satellite_image routes:', len(satellite_image.router.routes))
for r in satellite_image.router.routes:
    print(f'  {r.methods} {r.path}')

from app.api.v1.endpoints import auth
print('auth routes:', len(auth.router.routes))

from app.api.v1.endpoints import user
print('user routes:', len(user.router.routes))

# Now check the main app
from app.main import app
print('app routes:', len(app.routes))
for r in app.routes:
    print(f'  {r.__class__.__name__}: {r}')

from app.api.v1.api import api_router
print('api_router routes:', len(api_router.routes))
