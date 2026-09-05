FROM nginx:alpine

COPY . /usr/share/nginx/html

# If config.js hasn't been created, fall back to the example so the
# container still serves a working app out of the box.
RUN if [ ! -f /usr/share/nginx/html/js/config.js ]; then \
      cp /usr/share/nginx/html/js/config.example.js /usr/share/nginx/html/js/config.js; \
    fi

EXPOSE 80
