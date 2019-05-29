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
            'country' => 'England'
        ]);

        DB::table('towers')->insert([
            'dove_id' => 'ABERAVON',
            'dedication' => 'S Mary',
            'area' => 'Port Talbot',
            'town' => 'Aberavon',
            'county' => 'West Glamorgan',
            'country' => 'Wales'
        ]);
    }
}
