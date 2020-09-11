
var PermissionsMixin = {

    data: function() {

        return {

            permissions: [],
        }
    },

    created: function () {

        var app = this;
        axios.get(PermissionUrl)
            .then(function (response) {

                app.permissions = response.data.results;
            }).catch(function (error) {

            this.$message.error(error);
        });
    }
};