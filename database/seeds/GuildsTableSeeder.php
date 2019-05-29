<?php

use Illuminate\Database\Seeder;

class GuildsTableSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        $bathWellsId = DB::table('guilds')->insertGetId([
            'name' => 'Bath & Wells'
        ]);

        DB::table('guilds')->insert([
            'name' => 'Bath Branch',
            'affiliated_to' => $bathWellsId
        ]);
    }
}
