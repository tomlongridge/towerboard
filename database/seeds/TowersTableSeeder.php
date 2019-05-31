<?php

use Illuminate\Database\Seeder;

class TowersTableSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        DB::table('towers')->insert([
            'dove_id' => 'BATH BW',
            'dedication' => 'St Mary the Virgin',
            'area' => 'Bathwick',
            'town' => 'Bath',
            'county' => 'Somerset',
            'country' => 'England',
            'num_bells' => 10,
            'weight' => '18-3-20'
            ]);

            DB::table('towers')->insert([
            'dove_id' => 'ABERAVON',
            'dedication' => 'S Mary',
            'town' => 'Aberavon',
            'county' => 'West Glamorgan',
            'country' => 'Wales',
            'num_bells' => 6
        ]);
    }
}
