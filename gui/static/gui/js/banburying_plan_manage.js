;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                tableData: [{
                        "equip_no":"1#HWN-1",
                        "sn":1,
                        "product_no":"product_no_1",
                        "stage":"stage_1",
                        "actual_time":"70",
                        "plan_weight":"190",
                        "plan_trains":"200",
                        "actual_trains":"190",
                        "actual_weight":"200",
                        "ach_rate":100,
                        "plan_time":"80",
                        "start_rate":60
                    },
                    {
                        "equip_no":"1#HWN-2",
                        "sn":2,
                        "product_no":"product_no_2",
                        "stage":"stage_2",
                        "actual_time":"60",
                        "plan_weight":"200",
                        "plan_trains":"210",
                        "actual_trains":"200",
                        "actual_weight":"210",
                        "ach_rate":60,
                        "plan_time":"60",
                        "start_rate":60
                    },
                    {
                        "equip_no":"2#HWN-1",
                        "sn":1,
                        "product_no":"product_no_3",
                        "stage":"stage_1",
                        "actual_time":"60",
                        "plan_weight":"300",
                        "plan_trains":"310",
                        "actual_trains":"300",
                        "actual_weight":"310",
                        "ach_rate":19,
                        "plan_time":"90",
                        "start_rate":60
                    }],
                search_time:null,
                equip_no:null,
            }
        },

        // created: function () {
        //
        //     var app = this;
        //     axios.get(BanburyPlanUrl, {
        //     }).then(function (response) {
        //         app.tableData = response.data.data;
        //     }).catch(function (error) {
        //     });
        //
        //
        // },


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