
export default {

  async fetch(request, env) {

    const url = new URL(request.url);



    if (url.pathname.startsWith("/api/")) {

      return new Response(

        JSON.stringify({

          success: false,

          error: "AttendX API is running on the Flask backend"

        }),

        {

          status: 503,

          headers: {

            "content-type": "application/json"

          }

        }

      );

    }



    return env.ASSETS.fetch(request);

  }

};

