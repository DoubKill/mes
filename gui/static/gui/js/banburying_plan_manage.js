;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                tableData: [],
                search_time:null,
                equip_no:null,
            }
        },

        created: function () {

            var app = this;
            axios.get(BanburyPlanUrl, {
            }).then(function (response) {
                app.tableData = response.data.results;
            }).catch(function (error) {
            });


        },


        methods: {

            customColorMethod(percentage) {
                if (percentage < 20) {
                  return '#f56c6c';
                } else if (percentage < 40) {
                  return '#e6a23c';
                } else if (percentage < 60) {
                  return '#6f7ad3';
                } else if (percentage < 80) {
                  return '#1989fa';
                } else {
                  return '#5cb87a';
                }
              },

            getList() {
                var app = this;
                var param_url = BanburyPlanUrl;
                if(app.search_time && app.equip_no){
                    param_url = param_url + '?search_time=' +app.search_time + '&equip_no=' + app.equip_no
                }
                else if(!app.search_time && app.equip_no){
                    param_url = param_url + '?search_time=' + '&equip_no=' + app.equip_no
                }
                else if(app.search_time && !app.equip_no){
                    param_url = param_url + '?search_time=' +app.search_time + '&equip_no='
                }

                axios.get(param_url, {}
                ).then(function (response) {
                    app.tableData = response.data.data;
                }).catch(function (error) {
                    app.$message({
                        message: error.response.data,
                        type: 'error'
                    });
                });
            },

            SearchBanburyPlan: function(){
                this.getList()

            },

            search_timeChange: function(){
                this.getList()
            },

            equip_noChange: function() {
                this.getList()
            },


            handleCurrentChange: function (val) {

                this.currentRow = val;
            },
            currentChange() {
            },
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();